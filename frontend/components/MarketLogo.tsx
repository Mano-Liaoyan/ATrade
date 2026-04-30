type MarketLogoProps = {
  exchange?: string | null;
  provider?: string | null;
  compact?: boolean;
};

type MarketBadgeConfig = {
  label: string;
  shortCode: string;
  className: string;
};

const MARKET_BADGES: Record<string, MarketBadgeConfig> = {
  NASDAQ: { label: 'NASDAQ Stock Market', shortCode: 'NQ', className: 'market-logo--nasdaq' },
  NAS: { label: 'NASDAQ Stock Market', shortCode: 'NQ', className: 'market-logo--nasdaq' },
  NYSE: { label: 'New York Stock Exchange', shortCode: 'NY', className: 'market-logo--nyse' },
  NYS: { label: 'New York Stock Exchange', shortCode: 'NY', className: 'market-logo--nyse' },
  ARCA: { label: 'NYSE Arca', shortCode: 'AR', className: 'market-logo--arca' },
  AMEX: { label: 'NYSE American', shortCode: 'AM', className: 'market-logo--nyse' },
  LSE: { label: 'London Stock Exchange', shortCode: 'LN', className: 'market-logo--lse' },
  LON: { label: 'London Stock Exchange', shortCode: 'LN', className: 'market-logo--lse' },
  TSX: { label: 'Toronto Stock Exchange', shortCode: 'TO', className: 'market-logo--tsx' },
  TSE: { label: 'Toronto Stock Exchange', shortCode: 'TO', className: 'market-logo--tsx' },
  HKEX: { label: 'Hong Kong Exchange', shortCode: 'HK', className: 'market-logo--hkex' },
  SEHK: { label: 'Hong Kong Exchange', shortCode: 'HK', className: 'market-logo--hkex' },
  SMART: { label: 'IBKR SMART routing', shortCode: 'IB', className: 'market-logo--smart' },
};

const FALLBACK_BADGE: MarketBadgeConfig = {
  label: 'Provider market',
  shortCode: 'MK',
  className: 'market-logo--fallback',
};

export function MarketLogo({ exchange, provider, compact = false }: MarketLogoProps) {
  const normalizedExchange = normalizeMarketCode(exchange);
  const normalizedProvider = normalizeMarketCode(provider);
  const config = MARKET_BADGES[normalizedExchange] ?? getProviderFallback(normalizedProvider) ?? FALLBACK_BADGE;
  const displayExchange = normalizedExchange || normalizedProvider || 'market';

  return (
    <span
      className={`market-logo ${config.className}${compact ? ' market-logo--compact' : ''}`}
      aria-label={`${config.label} badge for ${displayExchange}`}
      title={`${config.label} (${displayExchange})`}
    >
      <span className="market-logo__mark" aria-hidden="true">{config.shortCode}</span>
      <span className="market-logo__label">{displayExchange}</span>
    </span>
  );
}

export function formatMarketCode(exchange?: string | null): string {
  return normalizeMarketCode(exchange) || 'UNKNOWN';
}

function getProviderFallback(provider: string): MarketBadgeConfig | null {
  if (provider === 'IBKR') {
    return MARKET_BADGES.SMART;
  }

  return null;
}

function normalizeMarketCode(value?: string | null): string {
  return value?.trim().toUpperCase() ?? '';
}
