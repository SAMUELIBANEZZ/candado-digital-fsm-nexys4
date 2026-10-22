# Crea el proyecto de Vivado para el candado digital (Nexys4 DDR / Nexys A7-100T).
#
# Uso, desde la raíz del repositorio:
#     vivado -mode batch -source vivado/create_project.tcl
# o bien, desde la consola Tcl de Vivado:
#     source vivado/create_project.tcl
#
# NOTA: estos scripts no se pudieron ejecutar en el entorno donde se generó el
# repositorio (no hay Vivado); el VHDL sí se verificó con GHDL. Si algún comando
# Tcl cambia entre versiones de Vivado, los pasos manuales equivalentes están en
# README.md y en el informe.

set proj_name  candado_fsm
set root       [file normalize [file join [file dirname [info script]] ..]]
set proj_dir   [file join $root vivado proj]

# XC7A100T-1CSG324C: FPGA de la Nexys4 DDR / Nexys A7-100T.
create_project -force $proj_name $proj_dir -part xc7a100tcsg324-1
set_property target_language VHDL [current_project]

# --- Síntesis: VHDL convertido desde Python (parámetros de hardware) ---------
add_files -norecurse [list \
    [file join $root hdl pck_myhdl_011.vhd] \
    [file join $root hdl candado_top.vhd]]
set_property top candado_top [current_fileset]

# --- Restricciones: asignación de pines -------------------------------------
add_files -fileset constrs_1 -norecurse [file join $root constraints candado_nexys4ddr.xdc]

# --- Simulación: mismo diseño con tiempos reducidos + testbench (VHDL-2008) --
add_files -fileset sim_1 -norecurse [list \
    [file join $root hdl candado_top_sim.vhd] \
    [file join $root sim tb_vectors_pkg.vhd] \
    [file join $root sim tb_candado_top.vhd]]
set_property file_type {VHDL 2008} [get_files tb_vectors_pkg.vhd]
set_property file_type {VHDL 2008} [get_files tb_candado_top.vhd]
set_property top tb_candado_top [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "Proyecto creado en $proj_dir"
