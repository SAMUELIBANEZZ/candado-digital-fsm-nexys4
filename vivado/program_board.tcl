# Programa la FPGA de la Nexys4 DDR / Nexys A7-100T con build/candado_top.bit.
#
# Conecte la placa por USB (PROG/UART), enciéndala (interruptor de alimentación)
# y ejecute, desde la raíz del repositorio:
#     vivado -mode batch -source vivado/program_board.tcl
# (Script no ejecutado en el entorno de desarrollo; ver nota en create_project.tcl.)

set root [file normalize [file join [file dirname [info script]] ..]]
set bit  [file join $root build candado_top.bit]
if {![file exists $bit]} {
    error "Falta $bit: ejecute antes vivado/build_bitstream.tcl"
}

open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices xc7a100t_0] 0]
current_hw_device $dev
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
puts "FPGA programada con $bit"
close_hw_target
disconnect_hw_server
close_hw_manager
