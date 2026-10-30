# Stock splits come from IBKR evidence and change the owner ledger and the stored bars

A stock split (forward split, reverse split, or bonus issue, US and HK) changes
the paper account position without a fill. ATrade finds a stock split from 2
IBKR values at no cost: the ratio between a stored daily close and the new
IBKR `TRADES` close of the same day (IBKR adjusts `TRADES` bars for splits),
and the ratio between the paper account position and the sum of the owner
positions. When the 2 ratios agree before the market opens, ATrade cancels the
open orders on the instrument, changes the owner ledger in one transaction, and
restarts the forward tests that trade the instrument. Each owner gets the
whole part of old shares times the split ratio, keeps its total cost, and gets
the part below 1 share as cash in lieu at the last close before the ex-date
divided by the split ratio. The remaining shares and cash go to "by hand", so
the owner positions always add up to the paper account position. ATrade also
records the stock split in a table and changes the stored bars of all bar
sources before the ex-date in place: prices divided by the split ratio, volume
times the split ratio. When the 2 values do not agree, the instrument is in
the "Split check needed" state: no owner can send an order on it until the
user applies the split or keeps the ledger. Decision:
[#149](https://github.com/Mano-Liaoyan/ATrade/issues/149), 2026-10-30.

## Considered options

- Buy corporate action data from Databento. It gives the ex-date before it
  comes, but the price starts at 299 USD each month, and the trial period
  accepts no monthly fees.
- Read the corporate action section of IBKR Flex reports. It has the real
  share count and cash in lieu, but it needs a new Flex token, and it is not
  known if it works for the paper account or on the ex-date.
- Let the user type each stock split. No detection errors, but a missed split
  makes the ledger wrong.
- Give the whole shares to the owners with the largest parts (largest
  remainder). The owner sum matches without "by hand", but a strategy then
  gets shares that it did not buy.
- Delete the stored IBKR bars and read them again. The prices are the same as
  IBKR, but 1-minute bars take about 2 minutes for each instrument and year,
  and Databento bars cannot be read again.

## Consequences

- Each bar read from IBKR also reads 1 stored daily bar, so each instrument
  can need 1 more request each day.
- The owner ledger has a "split adjustment" record next to fills. The "Fills"
  table of a forward test shows it as a row, and the equity includes the cash
  in lieu.
- Not checked before implementation, with the paper account: whether the
  paper account applies stock splits and cash in lieu, when, and how the TWS
  API reports them; whether IBKR adjusts the volume of `TRADES` bars by the
  split ratio; what a running `LiveNode` does when a position report has a
  new quantity (the restart avoids it).
- Cash dividends, spin-offs, mergers, symbol changes, and delistings are not
  handled. The paper trading page shows the difference as "Unattributed".
