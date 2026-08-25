# Single-clock 10 ns constraint for the out-of-context fpga_core Target.
create_clock -name clk -period 10.0 [get_ports clk]
