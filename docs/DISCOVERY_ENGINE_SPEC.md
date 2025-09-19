# DiscoveryEngine (Solana uutuustoken-seulonta)

## Lähteet
- DEX-pool eventit (Raydium/Orca/Meteora), Pump.fun, mempool/tx-virta, aggregaatit (vahvistus).
- Asynkroniset tuottajat -> Queue (TokenCandidate).

## Pikafiltterit
- min_liq_usd >= 3000
- top10_share <= 0.90
- LP locked/burned; jos ei JA authorityt ei renounced -> hylky

## Momentti & pisteytys
- novelty (ikä min), unique buyers 5m, buy/sell-suhde,
- liq_score, dist_score, - rug_risk.
- Kokonaispiste 0..1; kynnys ~0.65

## Integraatio
- `HybridTradingBot.discovery: DiscoveryEngine`
- `run_analysis_cycle()` -> `hot_candidates` listana
- Telegram-ilmoitukset: perusteltu yhteenveto

## Tallennus
- Perusmuisti ensin; deduplikointi mint-osoitteella. (DB myöhemmin)
