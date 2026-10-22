-- Testbench auto-verificable del candado digital.
--
-- Aplica a candado_top_sim (VHDL convertido desde Python con tiempos
-- reducidos) las mismas entradas que se simularon en Python y compara TODAS las
-- salidas de los pines (LED, SEG, DP, AN, LED RGB, UART) en cada ciclo contra lo
-- que produjo el modelo Python. Los vectores vienen de tb_vectors_pkg.vhd
-- (generado por tools/generate_vectors.py).
--
-- Temporización (igual que en Python): reloj de 10 ns con flancos de subida en
-- 5 + 10k ns; las entradas del ciclo k se aplican en t = 10k y las salidas se
-- muestrean en t = 10k + 9 ns.
--
-- Requiere VHDL-2008 (std.env.finish). En Vivado: tipo de archivo "VHDL 2008"
-- para este archivo y para tb_vectors_pkg.vhd.

library ieee;
use ieee.std_logic_1164.all;
use std.env.all;
use work.tb_vectors_pkg.all;

entity tb_candado_top is
end entity tb_candado_top;

architecture sim of tb_candado_top is
  constant MAX_REPORTED : natural := 20;

  signal clk          : std_logic := '0';
  signal CPU_RESETN   : std_logic := '1';
  signal SW           : std_logic_vector(15 downto 0) := (others => '0');
  signal BTNC, BTNU, BTND, BTNL, BTNR : std_logic := '0';
  signal LED          : std_logic_vector(15 downto 0);
  signal SEG          : std_logic_vector(6 downto 0);
  signal DP           : std_logic;
  signal AN           : std_logic_vector(7 downto 0);
  signal LED16_R, LED16_G, LED16_B : std_logic;
  signal UART_RXD_OUT : std_logic;

  function to_hex(v : std_logic_vector) return string is
    variable r      : string(1 to (v'length + 3) / 4);
    variable padded : std_logic_vector(4 * r'length - 1 downto 0) := (others => '0');
    variable nib    : std_logic_vector(3 downto 0);
  begin
    padded(v'length - 1 downto 0) := v;
    for i in r'range loop
      nib := padded(4 * (r'length - i) + 3 downto 4 * (r'length - i));
      case nib is
        when "0000" => r(i) := '0'; when "0001" => r(i) := '1';
        when "0010" => r(i) := '2'; when "0011" => r(i) := '3';
        when "0100" => r(i) := '4'; when "0101" => r(i) := '5';
        when "0110" => r(i) := '6'; when "0111" => r(i) := '7';
        when "1000" => r(i) := '8'; when "1001" => r(i) := '9';
        when "1010" => r(i) := 'A'; when "1011" => r(i) := 'B';
        when "1100" => r(i) := 'C'; when "1101" => r(i) := 'D';
        when "1110" => r(i) := 'E'; when "1111" => r(i) := 'F';
        when others => r(i) := 'X';
      end case;
    end loop;
    return r;
  end function;
begin
  clk <= not clk after 5 ns;

  dut : entity work.candado_top_sim
    port map (
      CLK100MHZ    => clk,
      CPU_RESETN   => CPU_RESETN,
      SW           => SW,
      BTNC         => BTNC,
      BTNU         => BTNU,
      BTND         => BTND,
      BTNL         => BTNL,
      BTNR         => BTNR,
      LED          => LED,
      SEG          => SEG,
      DP           => DP,
      AN           => AN,
      LED16_R      => LED16_R,
      LED16_G      => LED16_G,
      LED16_B      => LED16_B,
      UART_RXD_OUT => UART_RXD_OUT);

  driver_checker : process
    variable ii, oi, si : natural := 0;
    variable cur_in     : in_word_t;
    variable expected   : out_word_t := (others => 'U');
    variable actual     : out_word_t;
    variable errors     : natural := 0;
    variable scen_name  : string(1 to NAME_LEN) := (others => ' ');
    variable scen_start : natural := 0;
  begin
    for k in 0 to N_CYCLES - 1 loop
      -- nombre del escenario en curso (para los mensajes)
      while si < N_SCEN and SCENARIOS(si).cyc <= k loop
        scen_name  := SCENARIOS(si).name;
        scen_start := SCENARIOS(si).cyc;
        si := si + 1;
      end loop;

      -- t = 10k: aplicar entradas
      while ii < N_IN and IN_EVENTS(ii).cyc = k loop
        cur_in     := IN_EVENTS(ii).val;
        CPU_RESETN <= cur_in(21);
        BTNC       <= cur_in(20);
        BTNU       <= cur_in(19);
        BTND       <= cur_in(18);
        BTNL       <= cur_in(17);
        BTNR       <= cur_in(16);
        SW         <= cur_in(15 downto 0);
        ii := ii + 1;
      end loop;

      -- t = 10k + 9: comparar salidas
      wait for 9 ns;
      while oi < N_OUT and OUT_EVENTS(oi).cyc = k loop
        expected := OUT_EVENTS(oi).val;
        oi := oi + 1;
      end loop;
      actual := LED & SEG & DP & AN & LED16_R & LED16_G & LED16_B & UART_RXD_OUT;
      if actual /= expected then
        errors := errors + 1;
        if errors <= MAX_REPORTED then
          report "DIFERENCIA en ciclo " & integer'image(k) &
                 " (escenario '" & scen_name & "', ciclo local " &
                 integer'image(k - scen_start) & ") esperado=" & to_hex(expected) &
                 " obtenido=" & to_hex(actual)
            severity error;
        end if;
      end if;
      wait for 1 ns;
    end loop;

    report "Ciclos comparados: " & integer'image(N_CYCLES) &
           " | escenarios: " & integer'image(N_SCEN) &
           " | diferencias: " & integer'image(errors);
    if errors = 0 then
      report "PASS: el VHDL convertido coincide con el modelo Python en todos los ciclos.";
      finish;
    else
      report "FAIL: el VHDL convertido NO coincide con el modelo Python." severity failure;
    end if;
    wait;
  end process driver_checker;
end architecture sim;
