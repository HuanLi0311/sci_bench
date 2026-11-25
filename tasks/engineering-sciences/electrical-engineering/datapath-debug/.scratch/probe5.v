`timescale 1ns/1ps
module tb_probe;
    reg clk=0, rst=1;
    wire [31:0] ok_count, err_count, beats, stalled;
    wire gen_done; wire [7:0] sig; wire [15:0] first_bad;
    top u(.clk(clk),.rst(rst),.ok_count(ok_count),.err_count(err_count),
          .gen_done(gen_done),.beats(beats),.stalled(stalled),.sig(sig),.first_bad(first_bad));
    always #1 clk=~clk;
    integer lost=0, shown=0;
    always @(posedge clk) if (!rst && u.u_src.retire && !u.u_fifo.do_wr) begin
      lost=lost+1;
      if (shown<6) begin
        $display("t=%0t LOST beat=%0d full=%0d cnt=%0d credit=%0d valid=%0d rd=%0d",
          $time, u.s_data, u.f_full, u.u_fifo.count, u.u_src.credit, u.s_valid, u.u_fifo.do_rd);
        shown=shown+1;
      end
    end
    integer g;
    initial begin
      repeat(6) @(posedge clk); @(negedge clk); rst=0; g=0;
      while(!gen_done && g<40000) begin @(posedge clk); g=g+1; end
      repeat(256) @(posedge clk);
      $display("lost=%0d", lost);
      $finish;
    end
endmodule
