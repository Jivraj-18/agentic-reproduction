import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
print(wb.sheetnames)
for name in sys.argv[2:]:
    ws = wb[name]
    print("=====", name, ws.max_row, ws.max_column)
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 80)):
        vals = [(c.coordinate, c.value, (c.fill.fgColor.rgb if c.fill and c.fill.fill_type else None)) for c in row if c.value is not None]
        if vals:
            print(" | ".join(f"{a}={b}" + (f"[{f}]" if f and f!='00000000' else "") for a,b,f in vals))
