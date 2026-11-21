from ie.esco_map import norm


def test_norm_bo_chu_thich_trong_ngoac():
    assert norm("Java (computer programming)") == norm("java")


def test_norm_khong_phan_biet_hoa_thuong_va_dau_cham():
    assert norm("ASP.NET") == norm("asp net")


def test_norm_khong_gop_ten_khac_nhau():
    assert norm("C#") != norm("C++")
