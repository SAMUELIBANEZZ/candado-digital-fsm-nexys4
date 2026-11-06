## Candado digital (FSM) - asignación de pines para Nexys4 DDR / Nexys A7-100T
## FPGA: Xilinx Artix-7 XC7A100T-1CSG324C
##
## Archivo generado por tools/generate_xdc.py a partir del XDC maestro oficial de
## Digilent (https://github.com/Digilent/digilent-xdc, Nexys-A7-100T-Master.xdc).
## Los nombres de puerto coinciden con la entidad candado_top (hdl/candado_top.vhd).
## Hecho para la Nexys4 DDR. Para una Nexys4 ORIGINAL (no DDR) los pines de botones,
## display y audio son otros: usar el XDC maestro de esa placa.

## Reloj y reset
set_property -dict { PACKAGE_PIN E3   IOSTANDARD LVCMOS33 } [get_ports { CLK100MHZ }]; # Reloj de 100 MHz (sincronización, antirrebote y temporizadores)
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports { CLK100MHZ }];
set_property -dict { PACKAGE_PIN C12  IOSTANDARD LVCMOS33 } [get_ports { CPU_RESETN }]; # Botón rojo CPU RESET (activo en bajo): reset duro, restaura el código de fábrica

## Switches
set_property -dict { PACKAGE_PIN J15  IOSTANDARD LVCMOS33 } [get_ports { SW[0] }]; # SW0: bit 0 del dígito a ingresar (SW3..SW0)
set_property -dict { PACKAGE_PIN L16  IOSTANDARD LVCMOS33 } [get_ports { SW[1] }]; # SW1: bit 1 del dígito a ingresar (SW3..SW0)
set_property -dict { PACKAGE_PIN M13  IOSTANDARD LVCMOS33 } [get_ports { SW[2] }]; # SW2: bit 2 del dígito a ingresar (SW3..SW0)
set_property -dict { PACKAGE_PIN R15  IOSTANDARD LVCMOS33 } [get_ports { SW[3] }]; # SW3: bit 3 del dígito a ingresar (SW3..SW0)
set_property -dict { PACKAGE_PIN R17  IOSTANDARD LVCMOS33 } [get_ports { SW[4] }]; # SW4: sin función
set_property -dict { PACKAGE_PIN T18  IOSTANDARD LVCMOS33 } [get_ports { SW[5] }]; # SW5: sin función
set_property -dict { PACKAGE_PIN U18  IOSTANDARD LVCMOS33 } [get_ports { SW[6] }]; # SW6: sin función
set_property -dict { PACKAGE_PIN R13  IOSTANDARD LVCMOS33 } [get_ports { SW[7] }]; # SW7: sin función
set_property -dict { PACKAGE_PIN T8   IOSTANDARD LVCMOS18 } [get_ports { SW[8] }]; # SW8: sin función
set_property -dict { PACKAGE_PIN U8   IOSTANDARD LVCMOS18 } [get_ports { SW[9] }]; # SW9: sin función
set_property -dict { PACKAGE_PIN R16  IOSTANDARD LVCMOS33 } [get_ports { SW[10] }]; # SW10: sin función
set_property -dict { PACKAGE_PIN T13  IOSTANDARD LVCMOS33 } [get_ports { SW[11] }]; # SW11: sin función
set_property -dict { PACKAGE_PIN H6   IOSTANDARD LVCMOS33 } [get_ports { SW[12] }]; # SW12: sin función
set_property -dict { PACKAGE_PIN U12  IOSTANDARD LVCMOS33 } [get_ports { SW[13] }]; # SW13: sin función
set_property -dict { PACKAGE_PIN U11  IOSTANDARD LVCMOS33 } [get_ports { SW[14] }]; # SW14: sin función
set_property -dict { PACKAGE_PIN V10  IOSTANDARD LVCMOS33 } [get_ports { SW[15] }]; # SW15: sin función

## Pulsadores
set_property -dict { PACKAGE_PIN N17  IOSTANDARD LVCMOS33 } [get_ports { BTNC }]; # BTNC: confirma el dígito seleccionado en SW3..SW0
set_property -dict { PACKAGE_PIN M18  IOSTANDARD LVCMOS33 } [get_ports { BTNU }]; # BTNU: con el candado abierto (UNLOCKED) entra a CONFIG (cambiar código)
set_property -dict { PACKAGE_PIN P18  IOSTANDARD LVCMOS33 } [get_ports { BTND }]; # BTND: con el candado abierto (UNLOCKED) lo cierra de inmediato
set_property -dict { PACKAGE_PIN P17  IOSTANDARD LVCMOS33 } [get_ports { BTNL }]; # BTNL: borra el último dígito ingresado
set_property -dict { PACKAGE_PIN M17  IOSTANDARD LVCMOS33 } [get_ports { BTNR }]; # BTNR: cancelar, vuelve a LOCKED (no funciona en ALARM)

## LEDs LD15..LD0
set_property -dict { PACKAGE_PIN H17  IOSTANDARD LVCMOS33 } [get_ports { LED[0] }]; # LD0: dígitos ingresados (código termómetro)
set_property -dict { PACKAGE_PIN K15  IOSTANDARD LVCMOS33 } [get_ports { LED[1] }]; # LD1: dígitos ingresados (código termómetro)
set_property -dict { PACKAGE_PIN J13  IOSTANDARD LVCMOS33 } [get_ports { LED[2] }]; # LD2: dígitos ingresados (código termómetro)
set_property -dict { PACKAGE_PIN N14  IOSTANDARD LVCMOS33 } [get_ports { LED[3] }]; # LD3: dígitos ingresados (código termómetro)
set_property -dict { PACKAGE_PIN R18  IOSTANDARD LVCMOS33 } [get_ports { LED[4] }]; # LD4: intentos restantes (código termómetro)
set_property -dict { PACKAGE_PIN V17  IOSTANDARD LVCMOS33 } [get_ports { LED[5] }]; # LD5: intentos restantes (código termómetro)
set_property -dict { PACKAGE_PIN U17  IOSTANDARD LVCMOS33 } [get_ports { LED[6] }]; # LD6: intentos restantes (código termómetro)
set_property -dict { PACKAGE_PIN U16  IOSTANDARD LVCMOS33 } [get_ports { LED[7] }]; # LD7: intentos restantes (código termómetro)
set_property -dict { PACKAGE_PIN V16  IOSTANDARD LVCMOS33 } [get_ports { LED[8] }]; # LD8: intentos restantes (código termómetro)
set_property -dict { PACKAGE_PIN T15  IOSTANDARD LVCMOS33 } [get_ports { LED[9] }]; # LD9: sin función (apagado)
set_property -dict { PACKAGE_PIN U14  IOSTANDARD LVCMOS33 } [get_ports { LED[10] }]; # LD10: sin función (apagado)
set_property -dict { PACKAGE_PIN T16  IOSTANDARD LVCMOS33 } [get_ports { LED[11] }]; # LD11: candado cerrado
set_property -dict { PACKAGE_PIN V15  IOSTANDARD LVCMOS33 } [get_ports { LED[12] }]; # LD12: modo configuración (CONFIG)
set_property -dict { PACKAGE_PIN V14  IOSTANDARD LVCMOS33 } [get_ports { LED[13] }]; # LD13: acceso concedido (UNLOCKED)
set_property -dict { PACKAGE_PIN V12  IOSTANDARD LVCMOS33 } [get_ports { LED[14] }]; # LD14: intento fallido (ERROR)
set_property -dict { PACKAGE_PIN V11  IOSTANDARD LVCMOS33 } [get_ports { LED[15] }]; # LD15: alarma activa (ALARM; en alarma parpadean todos los LEDs)

## LED RGB LD16
set_property -dict { PACKAGE_PIN N15  IOSTANDARD LVCMOS33 } [get_ports { LED16_R }]; # LED RGB LD16, canal rojo (color según estado)
set_property -dict { PACKAGE_PIN M16  IOSTANDARD LVCMOS33 } [get_ports { LED16_G }]; # LED RGB LD16, canal verde
set_property -dict { PACKAGE_PIN R12  IOSTANDARD LVCMOS33 } [get_ports { LED16_B }]; # LED RGB LD16, canal azul

## Display de 7 segmentos (cátodos CA..CG -> SEG[6:0], 'abcdefg')
set_property -dict { PACKAGE_PIN T10  IOSTANDARD LVCMOS33 } [get_ports { SEG[6] }]; # Segmento a (cátodo CA, activo en bajo) = SEG[6]
set_property -dict { PACKAGE_PIN R10  IOSTANDARD LVCMOS33 } [get_ports { SEG[5] }]; # Segmento b (cátodo CB, activo en bajo) = SEG[5]
set_property -dict { PACKAGE_PIN K16  IOSTANDARD LVCMOS33 } [get_ports { SEG[4] }]; # Segmento c (cátodo CC, activo en bajo) = SEG[4]
set_property -dict { PACKAGE_PIN K13  IOSTANDARD LVCMOS33 } [get_ports { SEG[3] }]; # Segmento d (cátodo CD, activo en bajo) = SEG[3]
set_property -dict { PACKAGE_PIN P15  IOSTANDARD LVCMOS33 } [get_ports { SEG[2] }]; # Segmento e (cátodo CE, activo en bajo) = SEG[2]
set_property -dict { PACKAGE_PIN T11  IOSTANDARD LVCMOS33 } [get_ports { SEG[1] }]; # Segmento f (cátodo CF, activo en bajo) = SEG[1]
set_property -dict { PACKAGE_PIN L18  IOSTANDARD LVCMOS33 } [get_ports { SEG[0] }]; # Segmento g (cátodo CG, activo en bajo) = SEG[0]
set_property -dict { PACKAGE_PIN H15  IOSTANDARD LVCMOS33 } [get_ports { DP }]; # Punto decimal (activo en bajo; siempre apagado)

## Display de 7 segmentos (ánodos)
set_property -dict { PACKAGE_PIN J17  IOSTANDARD LVCMOS33 } [get_ports { AN[0] }]; # Ánodo del dígito 0 (activo en bajo): carácter 8 de 8 del texto
set_property -dict { PACKAGE_PIN J18  IOSTANDARD LVCMOS33 } [get_ports { AN[1] }]; # Ánodo del dígito 1 (activo en bajo): carácter 7 de 8 del texto
set_property -dict { PACKAGE_PIN T9   IOSTANDARD LVCMOS33 } [get_ports { AN[2] }]; # Ánodo del dígito 2 (activo en bajo): carácter 6 de 8 del texto
set_property -dict { PACKAGE_PIN J14  IOSTANDARD LVCMOS33 } [get_ports { AN[3] }]; # Ánodo del dígito 3 (activo en bajo): carácter 5 de 8 del texto
set_property -dict { PACKAGE_PIN P14  IOSTANDARD LVCMOS33 } [get_ports { AN[4] }]; # Ánodo del dígito 4 (activo en bajo): carácter 4 de 8 del texto
set_property -dict { PACKAGE_PIN T14  IOSTANDARD LVCMOS33 } [get_ports { AN[5] }]; # Ánodo del dígito 5 (activo en bajo): carácter 3 de 8 del texto
set_property -dict { PACKAGE_PIN K2   IOSTANDARD LVCMOS33 } [get_ports { AN[6] }]; # Ánodo del dígito 6 (activo en bajo): carácter 2 de 8 del texto
set_property -dict { PACKAGE_PIN U13  IOSTANDARD LVCMOS33 } [get_ports { AN[7] }]; # Ánodo del dígito 7 (activo en bajo): carácter 1 de 8 del texto

## UART (puente USB-UART de la placa)
set_property -dict { PACKAGE_PIN D4   IOSTANDARD LVCMOS33 } [get_ports { UART_RXD_OUT }]; # UART: transmisión al PC por el USB de la placa (registro de eventos, 115200 8N1)

## Audio de la placa y zumbador opcional en Pmod JA (alarma)
set_property -dict { PACKAGE_PIN A11  IOSTANDARD LVCMOS33 } [get_ports { AUD_PWM }]; # Salida de audio mono (jack de 3,5 mm): sirena de la alarma
set_property -dict { PACKAGE_PIN D12  IOSTANDARD LVCMOS33 } [get_ports { AUD_SD }]; # Habilitación del amplificador de audio (1 = encendido, sólo en ALARM)
set_property -dict { PACKAGE_PIN C17  IOSTANDARD LVCMOS33 } [get_ports { BUZZER }]; # Pmod JA1: zumbador piezoeléctrico pasivo opcional (entre JA1 y GND)

## Opciones de configuración (bancos a 3,3 V)
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
