// Intentional `doctor --deep` lint failure selected by [flows.lint.selftest].
// The undeclared RHS produces a hard Verilator error.
module bad_lint;
  wire booley_selftest_out;
  assign booley_selftest_out = booley_selftest_undeclared_signal;
endmodule
