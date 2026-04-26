def alu_model(data1, data2, alu_ctrl, c_in=0, z_in=0):
    data1 &= 0xFFFF
    data2 &= 0xFFFF

    if alu_ctrl == 0b00000:  # ADD
        res = data1 + data2
        carry = 1 if res > 0xFFFF else 0
        res &= 0xFFFF

    elif alu_ctrl == 0b00001:  # SUB
        res = (data1 - data2) & 0xFFFF
        carry = 0  # depends on your spec

    elif alu_ctrl == 0b00010:  # AND
        res = data1 & data2
        carry = 0

    else:
        res = 0
        carry = 0

    zero = 1 if res == 0 else 0
    lt = 1 if (data1 < data2) else 0
    eq = 1 if (data1 == data2) else 0
    le = 1 if (data1 <= data2) else 0

    return res, zero, carry, lt, eq, le
