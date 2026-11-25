`timescale 1ns/1ps
module tb_probe;
    reg clk=0, rst=1;
    wire [31:0] ok_count, err_count, beats, stalled;
    wire gen_done; wire [7:0] sig; wire [15:0] first_bad;
    top u(.clk(clk),.rst(rst),.ok_count(ok_count),.err_count(err_count),
          .gen_done(gen_done),.beats(beats),.stalled(stalled),.sig(sig),.first_bad(first_bad));
    always #1 clk=~clk;
    integer n_s=0,n_f=0,n_r=0,n_t=0,n_drop_f=0,gap=0;
    always @(posedge clk) if (!rst) begin
      if (u.s_valid && u.s_ready) n_s=n_s+1;
      if (u.s_valid && !u.s_ready && !u.u_src.credit && u.u_src.retire) n_drop_f=n_drop_f+1;
      if (u.f_valid && u.f_ready) n_f=n_f+1;
      if (u.r_valid && u.r_ready) n_r=n_r+1;
      if (u.t_valid && u.t_ready) n_t=n_t+1;
    end
    integer g;
    initial begin
      repeat(6) @(posedge clk); @(negedge clk); rst=0; g=0;
      while(!gen_done && g<40000) begin @(posedge clk); g=g+1; end
      repeat(128) @(posedge clk);
      $display("src_accepted=%0d src_lost=%0d fifo_out=%0d relay_out=%0d sink=%0d  OK=%0d ERR=%0d first_bad=%0d",
               n_s,n_drop_f,n_f,n_r,n_t,ok_count,err_count,first_bad);
      $finish;
    end
endmodule
