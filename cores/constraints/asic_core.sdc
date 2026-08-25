# 10 ns single-clock constraint for the RV32IMC synth_core Target.
create_clock -name clk -period 10.0 [get_ports clk]
