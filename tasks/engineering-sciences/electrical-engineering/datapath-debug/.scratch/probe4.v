`timescale 1ns/1ps
module tb_probe;
    reg clk=0, rst=1;
    wire [31:0] ok_count, err_count, beats, stalled;
    wire gen_done; wire [7:0] sig; wire [15:0] first_bad;
    top u(.clk(clk),.rst(rst),.ok_count(ok_count),.err_count(err_count),
          .gen_done(gen_done),.beats(beats),.stalled(stalled),.sig(sig),.first_bad(first_bad));
    always #1 clk=~clk;
    integer sent=0,wr=0,rd=0,rc=0,re=0,ti=0,to=0;
    always @(posedge clk) if (!rst) begin
      if (u.u_src.retire) sent=sent+1;
      if (u.u_fifo.do_wr) wr=wr+1;
      if (u.u_fifo.do_rd) rd=rd+1;
      if (u.u_relay.in_valid && u.u_relay.in_ready) rc=rc+1;
      if (u.r_valid && u.r_ready) re=re+1;
      if (u.t_valid && u.t_ready) to=to+1;
    end
    integer g;
    initial begin
      repeat(6) @(posedge clk); @(negedge clk); rst=0; g=0;
      while(!gen_done && g<40000) begin @(posedge clk); g=g+1; end
      repeat(256) @(posedge clk);
      $display("sent=%0d fifo_wr=%0d fifo_rd=%0d relay_in=%0d relay_out=%0d sink=%0d ok=%0d err=%0d",
               sent,wr,rd,rc,re,to,ok_count,err_count);
      $finish;
    end
endmodule
