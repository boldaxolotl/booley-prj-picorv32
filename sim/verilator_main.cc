// Verilator main for the upstream PicoRV32 testbenches (testbench.v and
// testbench_wb.v). Upstream hides their `testbench` modules from Verilator,
// so this file does their job around `picorv32_wrapper`:
//   - 10 ns clock starting high, counted as a rising edge at time 0 like
//     Icarus, then reset held for the next 100 rising edges;
//   - "TIMEOUT" after 1,000,000 rising edges, like the Icarus testbench;
//   - a VCD at testbench.vcd when Booley asks for a trace (+trace) or when
//     upstream's +vcd switch is given. (Upstream's +trace writes an
//     instruction trace instead; Booley's sim Flow passes +trace for waves.)
// Build with -CFLAGS -DPICORV32_WB_TB for testbench_wb.v, whose wrapper has
// wb_clk and an active-high wb_rst instead of clk and resetn.
//
// The sim Targets build a copy: .booley/hooks/post-setup.sh copies this file
// to testbench_verilator_main.cc in the checkout. Rerun the hook after edits.
#include <cstdio>
#include <cstring>
#include <memory>

#include "Vpicorv32_wrapper.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

namespace {

constexpr int kResetEdges = 100;        // rising edges held in reset
constexpr long kTimeoutEdges = 1000000; // rising edges before TIMEOUT
constexpr int kHalfPeriodNs = 5;

// True when `arg` (such as "+trace") is on the command line exactly, so
// "+tracefile=..." does not count.
bool has_exact_arg(int argc, char** argv, const char* arg) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], arg) == 0) return true;
    }
    return false;
}

void set_clock(Vpicorv32_wrapper& top, bool level) {
#ifdef PICORV32_WB_TB
    top.wb_clk = level;
#else
    top.clk = level;
#endif
}

void set_reset(Vpicorv32_wrapper& top, bool in_reset) {
#ifdef PICORV32_WB_TB
    top.wb_rst = in_reset;
#else
    top.resetn = !in_reset;
#endif
}

}  // namespace

int main(int argc, char** argv) {
    const auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
    const auto top = std::make_unique<Vpicorv32_wrapper>(context.get());

    std::unique_ptr<VerilatedVcdC> vcd;
    if (has_exact_arg(argc, argv, "+trace") || has_exact_arg(argc, argv, "+vcd")) {
        context->traceEverOn(true);
        vcd = std::make_unique<VerilatedVcdC>();
        top->trace(vcd.get(), 99);
        vcd->open("testbench.vcd");
    }

    // Icarus sees `reg clk = 1` as a rising edge at time 0; logic clocked on
    // every edge (the AXI test's random stall generator) counts it, so model
    // it too. Reset then holds for the next 100 edges and is released right
    // after the 100th, like the nonblocking `resetn <= 1` in testbench.v.
    set_reset(*top, true);
    set_clock(*top, false);
    top->eval();
    set_clock(*top, true);
    top->eval();
    if (vcd) vcd->dump(context->time());

    // Time steps are in the design's precision (1 ps from `timescale).
    long long half_period = kHalfPeriodNs;
    for (int exp = -9; exp > context->timeprecision(); --exp) half_period *= 10;

    long rising_edges = 0;  // after time 0
    bool clock = true;
    while (!context->gotFinish()) {
        context->timeInc(half_period);
        clock = !clock;
        set_clock(*top, clock);
        top->eval();
        if (clock) {
            ++rising_edges;
            if (rising_edges == kResetEdges) {
                set_reset(*top, false);
                top->eval();
            }
            if (rising_edges == kTimeoutEdges) {
                std::printf("TIMEOUT\n");
                break;
            }
        }
        if (vcd) vcd->dump(context->time());
    }

    if (vcd) vcd->close();
    top->final();
    return 0;
}
