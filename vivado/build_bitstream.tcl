# Síntesis, implementación y bitstream (modo batch).
#
# Uso, desde la raíz del repositorio:
#     vivado -mode batch -source vivado/build_bitstream.tcl
#
# Deja el bitstream en build/candado_top.bit y los reportes de utilización y
# temporización en vivado/reports/. (Script no ejecutado en el entorno de
# desarrollo; ver nota en create_project.tcl.)

set root [file normalize [file join [file dirname [info script]] ..]]
source [file join $root vivado create_project.tcl]

file mkdir [file join $root build]
file mkdir [file join $root vivado reports]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "La síntesis falló: revisar vivado/proj/*/synth_1/runme.log"
}

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    error "La implementación falló: revisar vivado/proj/*/impl_1/runme.log"
}

open_run impl_1
report_utilization    -file [file join $root vivado reports utilization.rpt]
report_timing_summary -file [file join $root vivado reports timing_summary.rpt]
report_drc            -file [file join $root vivado reports drc.rpt]

set bit [glob -nocomplain [file join $root vivado proj candado_fsm.runs impl_1 candado_top.bit]]
if {$bit eq ""} {
    error "No se encontró el bitstream generado"
}
file copy -force $bit [file join $root build candado_top.bit]
puts "Bitstream: [file join $root build candado_top.bit]"
