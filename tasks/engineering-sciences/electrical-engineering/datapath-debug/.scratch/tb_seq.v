
`timescale 1ns/1ps
module tb_seq;
    reg clk=0, rst=1;
    reg [15:0] in_data=0; reg in_valid=1;
    wire in_ready; wire [31:0] ok_count, err_count; wire [15:0] last_seen, first_bad;
    seq_check u(.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ready(in_ready),
                .ok_count(ok_count), .err_count(err_count), .last_seen(last_seen), .first_bad(first_bad));
    always #1 clk=~clk;
    always @(posedge clk) begin
        if (rst) in_data <= 16'd0;
        else if (in_valid && in_ready) in_data <= in_data + 16'd1;
    end
    initial begin
        repeat(3) @(posedge clk);
        @(negedge clk); rst=0;
        repeat(600) @(posedge clk);
        $display("SEQ_OK=%0d SEQ_ERR=%0d", ok_count, err_count);
        $finish;
    end
endmodule
