# Blog Outline: Hyperliquid Builder Codes - The Opportunity and How to Track It

**Accompanying YouTube Video:** Real-Time Hyperliquid Builders Dashboard with gRPC & React

---

## Title Options

- "Hyperliquid Builder Codes: A $10M+ Developer Revenue Opportunity"
- "How Builders Are Earning Millions on Hyperliquid (And How to Track Them)"
- "The Builder Code Gold Rush: Understanding Hyperliquid's Developer Economy"

---

## Introduction (Hook)

- Builder codes on Hyperliquid have generated over $9.5M in revenue so far
- Third-party builders now drive approximately 1/3 of Hyperliquid's trading volume
- This represents one of the most significant developer revenue opportunities in DeFi
- We built a real-time dashboard to track this emerging ecosystem

---

## Section 1: What Are Hyperliquid Builder Codes?

### Key Points:
- Builder codes allow developers ("builders") to receive a fee on trades they route to Hyperliquid
- Unlike centralized exchanges that keep all fees, Hyperliquid shares revenue with front-end developers
- Fees are set per-order for flexibility (max 0.1% on perps, 1% on spot)
- Users must approve a maximum fee for each builder and can revoke permissions anytime
- Builders need at least 100 USDC in their perps account to participate

### How It Works:
1. User approves a builder via `ApproveBuilderFee` action
2. Builder submits orders on behalf of user with their builder code attached
3. When orders fill, the builder earns the specified fee
4. Fees are claimed through Hyperliquid's referral reward system

**Sources:**
- [Builder codes | Hyperliquid Docs](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/builder-codes)
- [Builder Codes | Hyperliquid Wiki](https://hyperliquid-co.gitbook.io/wiki/guide/builder-guide/hypercore/builder-codes)

---

## Section 2: The Opportunity - By the Numbers

### Current State:
- ~$9.5M+ total builder code revenue generated
- @pvp_dot_trade leads with ~$7.2M in builder fee revenue
- 22+ active builders capturing volume
- Approximately 1/3 of Hyperliquid's trading flow comes from third-party builders

### Why This Matters:
- Traditional DEXs: Developers build for free, protocol takes all fees
- Hyperliquid model: Developers are incentivized to bring users and volume
- Creates a competitive marketplace of trading interfaces
- Some builders share revenue back with users (e.g., 50% revenue sharing models)

### Market Quote:
> "I've got a feeling we're going to see a builder code gold rush. Between this and HyperEVM eco giving utility to HYPE, we could see a genuine Hyperliquid wealth effect a la DeFi Summer."

**Sources:**
- [Hyperliquid Builder Codes Top $10M](https://www.bitget.com/news/detail/12560604858641)
- [Charlie.hl on X: Builder Codes Analysis](https://x.com/0xBroze/status/1938603649917153661)
- [Builder Revenue Dashboard](https://hyperliquid.allium.so/builder-revenue)

---

## Section 3: The Future - HIP-3 and Beyond

### What is HIP-3?
- Allows third-party developers to create their own markets on Hyperliquid
- Opens up: stocks, prediction markets, commodities, yield-bearing stablecoin collateral
- Transforms Hyperliquid into an "everything exchange"

### Combined with Builder Codes:
- Developers can create custom markets AND earn fees on trading
- Full vertical integration: build the market, build the interface, capture the value
- Expected to significantly increase Hyperliquid's total trading volume by 2026

### Competitive Landscape:
- Paradex and Lighter now offer zero-fee builder codes with revenue sharing
- Competition is driving innovation in builder incentive models
- More builders entering = more competition for revenue

**Sources:**
- [HIP-3 and Builder Codes Market Analysis](https://www.bitget.com/news/detail/12560605111420)
- [How Builder Codes Are Revolutionizing Developer Income | OKX](https://www.okx.com/en-us/learn/builder-hyperliquid-developer-income)

---

## Section 4: Building a Real-Time Builder Tracker

### Why We Built This Dashboard:
- Track builder fee revenue in real-time
- Understand market share dynamics
- Monitor the health of the builder ecosystem
- Learn gRPC streaming with a practical example

### Technical Architecture:
```
Hyperliquid L1 --[gRPC Stream]--> Python Backend --[WebSocket]--> React Frontend
```

### Key Technologies:
- **gRPC Streaming**: Real-time fill events from Hyperliquid L1
- **Python FastAPI**: Processes fills, aggregates statistics
- **WebSocket**: Pushes live updates to browser
- **React + TypeScript**: Responsive dashboard UI

### What We Track:
- Total builder fee revenue (USD stablecoins only)
- Trading volume per builder
- Unique users per builder
- Real-time rankings

### Code Repository:
- Link to GitHub repo
- Uses Dwellir's gRPC endpoint for reliable blockchain data access

---

## Section 5: Getting Started as a Builder

### Requirements:
1. At least 100 USDC in perps account value
2. Contact Hyperliquid team or register via documentation
3. Build a frontend or trading interface
4. Implement the builder code in your order submissions

### Resources:
- [Python SDK Builder Fee Example](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/examples/basic_builder_fee.py)
- [Privy Docs - Builder Codes Integration](https://docs.privy.io/recipes/hyperliquid/builder-codes)
- [Hyperliquid Builder Stats](https://hypebuilders.xyz/)

### Things to Consider:
- Fee competition (can't exceed 0.1% on perps)
- User acquisition strategy
- Value proposition vs. native interface
- Revenue sharing with users as differentiation

---

## Section 6: Challenges and Risks

### Potential Issues:
- **Competition**: More builders = smaller individual share
- **Gaming/Misuse**: Potential for artificial volume generation
- **Fee Compression**: Competitors offering lower/zero fees
- **Dependency**: Revenue tied to Hyperliquid's success

### Data Point:
- Total revenue has remained stable despite more participants
- Individual rewards may be shrinking as competition increases

---

## Conclusion

### Key Takeaways:
1. Builder codes represent a paradigm shift in how DEXs share value with developers
2. Nearly $10M already generated with significant room for growth
3. HIP-3 will expand opportunities even further
4. Tools like our dashboard help track this emerging ecosystem
5. Now is the time to explore building on Hyperliquid

### Call to Action:
- Watch the YouTube video for technical deep-dive
- Clone the dashboard repo and explore the code
- Consider building your own trading interface
- Follow builder code revenue trends at hypebuilders.xyz

---

## Additional Resources

### Official Documentation:
- [Hyperliquid Docs - Builder Codes](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/builder-codes)
- [Hyperliquid Docs - Fees](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees)

### Analytics:
- [Hyperliquid Builder Stats](https://hypebuilders.xyz/)
- [DefiLlama - Hyperliquid Fees](https://defillama.com/fees/chain/hyperliquid-l1)
- [Allium Builder Revenue Dashboard](https://hyperliquid.allium.so/builder-revenue)

### Infrastructure:
- [Dwellir](https://dwellir.com) - Blockchain infrastructure and gRPC endpoints

---

## SEO Keywords

- Hyperliquid builder codes
- Hyperliquid developer revenue
- DeFi builder economy
- Hyperliquid gRPC API
- Real-time trading dashboard
- HIP-3 Hyperliquid
- Blockchain developer income
- DEX revenue sharing

---

## Social Media Snippets

### Twitter/X Thread Hook:
"Builder codes on Hyperliquid have generated over $9.5M in revenue. Here's why this might be the biggest developer opportunity in DeFi right now..."

### LinkedIn Summary:
"Hyperliquid is pioneering a new model where front-end developers earn direct revenue from trading volume. With $10M+ already paid to builders and HIP-3 on the horizon, this could reshape how we think about DEX economics."
