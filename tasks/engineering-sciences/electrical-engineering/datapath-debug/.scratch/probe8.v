`timescale 1ns/1ps
module tb_probe;
    reg clk=0, rst=1;
    wire [31:0] ok_count, err_count, beats, stalled;
    wire gen_done; wire [7:0] sig; wire [15:0] first_bad;
    top u(.clk(clk),.rst(rst),.ok_count(ok_count),.err_count(err_count),
          .gen_done(gen_done),.beats(beats),.stalled(stalled),.sig(sig),.first_bad(first_bad));
    always #1 clk=~clk;
    integer shown=0;
    always @(posedge clk) if (!rst && u.u_src.retire && !u.u_fifo.do_wr && shown<3) begin
      shown=shown+1;
      $display("t=%0t n=%0d valid=%0d full=%0d cnt=%0d in_ready=%0d do_wr=%0d do_rd=%0d out_valid=%0d out_ready=%0d thr_take=%0d",
        $time,u.u_src.n,u.s_valid,u.f_full,u.u_fifo.count,u.u_fifo.in_ready,u.u_fifo.do_wr,
        u.u_fifo.do_rd,u.f_valid,u.f_ready,u.u_thr.take);
    end
    integer g;
    initial begin
      repeat(6) @(posedge clk); @(negedge clk); rst=0; g=0;
      while(!gen_done && g<60000) begin @(posedge clk); g=g+1; end
      $finish;
    end
endmodule
