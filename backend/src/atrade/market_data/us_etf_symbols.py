"""The ETF symbols that the quarterly US universe leaves out (docs/architecture/market_data.md sections 8.9, 8.14).

The purchase has no Databento `definition` data, so the daily bars do not tell an ETF from a common stock. Only the
instruments with the highest trading values can be members. Thus a list of the ETFs and ETNs with a high trading
value is sufficient. Add a symbol when an ETF shows in `us_universe_member`.
"""

US_ETF_SYMBOLS = frozenset(
    {
        # Broad market and size.
        "SPY", "VOO", "IVV", "VTI", "QQQ", "QQQM", "DIA", "IWM", "IWF", "IWD", "IWB", "IJH", "IJR", "MDY", "RSP",
        "VUG", "VTV", "VEA", "VWO", "VXUS", "EFA", "EEM", "IEFA", "IEMG", "SCHD", "SCHX", "SPLG", "SPYG", "SPYV",
        "VIG", "VYM", "MTUM", "USMV", "QUAL", "ARKK",
        # Sectors and industries.
        "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC", "SMH", "SOXX", "XBI",
        "IBB", "KRE", "KBE", "XOP", "XME", "XHB", "ITB", "XRT", "OIH", "GDX", "GDXJ", "JETS", "VNQ", "IYR",
        "IGV", "TAN", "ICLN", "URA", "KWEB", "FXI", "EWZ", "EWJ", "EWY", "EWT", "INDA", "MCHI", "ASHR",
        # Bonds, commodities, currencies, and volatility.
        "TLT", "IEF", "SHY", "LQD", "HYG", "JNK", "AGG", "BND", "TIP", "BIL", "SGOV", "SHV", "EMB", "MUB",
        "GLD", "IAU", "SLV", "USO", "UNG", "DBC", "UUP", "FXE", "VXX", "UVXY", "SVXY", "VIXY",
        "IBIT", "FBTC", "GBTC", "ETHA", "BITO",
        # Leveraged and inverse.
        "TQQQ", "SQQQ", "SPXL", "SPXS", "SPXU", "UPRO", "SDS", "SH", "PSQ", "QLD", "SSO", "TNA", "TZA",
        "SOXL", "SOXS", "TECL", "FAS", "FAZ", "LABU", "LABD", "NUGT", "DUST", "JNUG", "JDST", "TMF", "TMV",
        "UCO", "SCO", "BOIL", "KOLD", "YINN", "YANG", "FNGU", "FNGD", "BITX", "TSLL", "NVDL", "CONL", "MSTU",
    }
)  # fmt: skip
