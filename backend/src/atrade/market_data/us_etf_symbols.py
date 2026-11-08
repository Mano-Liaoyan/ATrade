"""The ETF symbols that the quarterly US universe leaves out (docs/architecture/market_data.md sections 8.9, 8.14) and
that the screen filter `not_etf` removes (docs/architecture/screen.md section 24.4.1).

The purchase has no Databento `definition` data, so the daily bars do not tell an ETF from a common stock. Only the
instruments with the highest trading values can be members. Thus a list of the ETFs and ETNs with a high trading
value is sufficient for the universe. The screen filter can start from all instruments with daily bars, so the list
also has more common ETFs, ETNs, and leveraged and inverse products. A symbol that is not in the list passes the
filter. Add a symbol when an ETF shows in `us_universe_member` or in a screen result with `not_etf`. A change of the
list changes only the quarters that the universe calculates after the change.
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
        # More broad market, size, style, and dividend ETFs.
        "VT", "ITOT", "SCHB", "SCHG", "SCHA", "SCHF", "VB", "VO", "VV", "VBR", "VBK", "VOE", "VOT", "MGK", "IWO",
        "IWN", "IWR", "IWS", "IWP", "IVW", "IVE", "OEF", "XLG", "SPMO", "SPHQ", "SPLV", "DGRO", "NOBL", "SDY",
        "HDV", "DVY", "COWZ", "JEPI", "JEPQ", "QYLD", "XYLD", "ACWI", "ACWX", "URTH", "EEMV", "EFAV", "SCZ", "VSS",
        # More sectors, industries, and themes.
        "VGT", "VHT", "VFH", "VDE", "VPU", "VIS", "VCR", "VDC", "VAW", "VOX", "FTEC", "IYW", "IYF", "IYH", "IYE",
        "IYM", "IYJ", "IYC", "IYZ", "IYT", "XTN", "XSD", "PSI", "IHI", "ITA", "XAR", "PPA", "PAVE", "IGF", "KIE",
        "IAI", "IAT", "XES", "IEO", "IEZ", "FDN", "XPH", "PBW", "QCLN", "LIT", "REMX", "COPX", "SIL", "SILJ",
        "URNM", "CIBR", "HACK", "SKYY", "BOTZ", "ROBO", "ARKG", "ARKW", "ARKF", "ARKQ", "BLOK", "MOO",
        # More countries and regions.
        "EWW", "EWC", "EWU", "EWG", "EWQ", "EWA", "EWH", "EWS", "EWL", "EWP", "EWI", "EZU", "VGK", "IEUR", "FEZ",
        "EPI", "INDY", "ARGT", "ECH", "EPOL", "TUR", "EIDO", "THD", "VNM", "KSA", "GXC", "CQQQ", "KBA", "ILF",
        "DXJ", "HEDJ",
        # More bonds and cash.
        "SPTL", "VGLT", "VGIT", "VGSH", "BSV", "BIV", "BLV", "VCIT", "VCSH", "IGIB", "IGSB", "SCHO", "SCHR",
        "SCHZ", "GOVT", "MBB", "VMBS", "BKLN", "SRLN", "SJNK", "USHY", "ANGL", "FLOT", "IEI", "TLH", "EDV",
        "ZROZ", "STIP", "VTIP", "SCHP", "VTEB", "BNDX", "EMLC", "PFF", "PGX", "USFR", "TFLO", "BOXX", "JPST",
        "MINT", "ICSH", "GBIL", "TBIL",
        # More commodities, crypto, and volatility.
        "GLDM", "SGOL", "PPLT", "PALL", "CPER", "DBA", "DBO", "USL", "BNO", "UGA", "CORN", "WEAT", "SOYB",
        "BITB", "ARKB", "HODL", "BRRR", "EZBC", "BTCO", "BTCW", "FETH", "ETHE", "ETHW", "VIXM", "UVIX", "SVIX",
        "SVOL", "TSLY", "NVDY", "CONY", "MSTY", "YMAX",
        # More leveraged and inverse index, sector, bond, and commodity products.
        "UDOW", "SDOW", "DDM", "DXD", "DOG", "QID", "URTY", "SRTY", "UWM", "TWM", "RWM", "SPDN", "MIDU", "TECS",
        "WEBL", "WEBS", "BULZ", "HIBL", "HIBS", "DPST", "CURE", "DRN", "DRV", "ERX", "ERY", "GUSH", "DRIP",
        "NAIL", "RETL", "UTSL", "DFEN", "TPOR", "TBT", "TBF", "UBT", "TYD", "TYO", "EDC", "EDZ", "EURL", "INDL",
        "CHAU", "CWEB", "KORU", "BRZU", "AGQ", "ZSL", "UGL", "GLL", "NRGU", "BITU", "BITI", "SBIT", "ETHU",
        # Single-stock leveraged and inverse products.
        "NVDU", "NVDX", "NVDQ", "NVDD", "NVDS", "TSLQ", "TSLZ", "TSLR", "TSLT", "TSLS", "MSTX", "MSTZ", "AAPU",
        "AAPD", "AMZU", "AMZD", "GGLL", "GGLS", "METU", "METD", "MSFU", "MSFD", "AMDL", "PLTU",
    }
)  # fmt: skip
