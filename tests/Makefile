TOPLEVEL_LANG = vhdl
SIM = ghdl

TOPLEVEL = top
MODULE = test_basic

VHDL_SOURCES = ../src/PC.vhdl \
               ../src/RegisterFile.vhdl \
               ../src/top.vhdl

RUN_ARGS=--vcd=wave.vcd

include $(shell cocotb-config --makefiles)/Makefile.sim
