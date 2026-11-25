`timescale 1ns/1ps
module tb_probe;
    reg clk=0, rst=1;
    wire [31:0] ok_count, err_count, beats, stalled;
    wire gen_done; wire [7:0] sig; wire [15:0] first_bad;
    top u(.clk(clk),.rst(rst),.ok_count(ok_count),.err_count(err_count),
          .gen_done(gen_done),.beats(beats),.stalled(stalled),.sig(sig),.first_bad(first_bad));
    always #1 clk=~clk;
    integer fifo_pop=0, rel_cap=0, rel_emit=0, thr_in=0, thr_out=0, bad_ovr=0, lost_id=0;
    always @(posedge clk) if (!rst) begin
      if (u.f_valid && u.f_ready) fifo_pop=fifo_pop+1;
      if (u.u_relay.take && u.f_valid) rel_cap=rel_cap+1;
      if (u.r_valid && u.r_ready) rel_emit=rel_emit+1;
      if (u.t_valid && u.t_ready) thr_in=thr_in+1;
      // overwrite detection: hold already has a beat but we take another
      if (u.u_relay.take && u.u_relay.b_valid && (!u.u_relay.out_valid || u.u_relay.out_ready)) bad_ovr=bad_ovr+1;
    end
    integer g;
    initial begin
      repeat(6) @(posedge clk); @(negedge clk); rst=0; g=0;
      while(!gen_done && g<40000) begin @(posedge clk); g=g+1; end
      repeat(128) @(posedge clk);
      $display("fifo_pop=%0d rel_cap=%0d rel_emit=%0d thr_in=%0d bad_ovr=%0d", fifo_pop,rel_cap,rel_emit,thr_in,bad_ovr);
      $finish;
    end
endmodule
