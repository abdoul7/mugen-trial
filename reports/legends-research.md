# Legends research notes — 2026-10-27

## What is established and what is our design

The four families and coaching mode were developed with the owner. The numerical
rules in docs/legends-design.md are proposed test values. The references below
support the original card identities and design inspiration, not our balance.

### Card-system research, completed before artwork generation

- **Pokémon TCG:** official rules separate Pokémon, Energy and Trainer functions,
  identify card fields and persistent game zones. Adopt readable roles and the
  distinction between held, equipped and discarded cards; do not import turns,
  six Prize cards or Energy attachments into a continuously fighting AI match.
  https://assets.pokemon.com/assets/cms2/pdf/trading-card-game/rulebook/swsh8_rulebook_en.pdf
- **Pokémon illustration rarity:** the official Scarlet & Violet aesthetic article
  describes full-art foil special illustration rares featuring a subject's traits
  or environment. Adopt increasing art coverage and narrative scene detail. The
  owner's requirement sets Legendary to full art in Legends; physical TCG rarity
  is not a universal power ranking.
  https://www.pokemon.com/uk/news/pokemon-tcg-scarlet-and-violet-revamps-pokemon-tcg-card-aesthetic
- **Yu-Gi-Oh!:** Konami explicitly separates conditions/timing, activation/costs
  and resolution. Adopt clear readiness, reservation, commitment and effect states.
  Its turn-based chains and response windows are not imported wholesale.
  https://www.yugioh-card.com/eu/play/understanding-card-text/part-3-conditions-activations-and-effects/
  https://www.yugioh-card.com/en/rulebook/
- **Dragon Ball Legends:** the official guide describes card-triggered Arts,
  Ki requirements, three selected battle fighters and conditional support effects.
  Adopt live card interventions and a three-fighter identity; our CPU coaching,
  Hype draws and separate-bout relay are original adaptations, not its rules.
  https://dble.bn-ent.net/en/howtoplay.html
- **Item Asylum:** the official Roblox description gives three random items in
  fixed melee/ranged/misc roles on respawn. Adopt understandable random roles and
  combinations, not its full item list or unrelated jokes.
  https://www.roblox.com/games/5670218884/item-asylum

### Reference research for the starter set

| Card | Reference evidence | Adaptation boundary |
|---|---|---|
| My Ninja Way | Naruto's official retrospective discusses the character's chosen path and contrasting convictions. https://naruto-official.com/en/news/01_1355 | Original Resolve name/AI profile; not a claim that Naruto canonically loses a fixed guard percentage. |
| Saiyan Pride | Vegeta's established Dragon Ball identity is used as character inspiration. | Original card/profile, not an official named move or canon numerical ability. |
| Scarlet Resolve | Kurapika's scarlet-eyed character presentation inspires the illustration. | Original named coaching profile; not Emperor Time and not a claim to reproduce that ability. |
| Chidori | Naruto's official Ninja Battle announcement identifies Sasuke's Chidori and Naruto's Rasengan as signature techniques. https://naruto-official.com/en/news/01_1728 | Shared lightning-rush echo requires original VFX and engine implementation; no arbitrary character-state call. |
| Spirit Gun | Licensed Kotobukiya Yusuke product explicitly presents the Spirit Gun. https://www.kotobukiya.co.jp/en/product/detail/P4934054058631/ | Authored projectile echo, no canon power scaling or guaranteed hit. |
| Bungee Gum | Official Nen x Impact Hisoka profile describes using Bungee Gum for pulling and spacing. https://hunterhunter-ni.bushiroad.com/en/character/hisoka/ | A short bounded tether on successful connection. |
| Kaio-ken | Official Dragon Ball material identifies Goku's red-glowing Kaio-ken technique. https://en.dragon-ball-official.com/news/01_2320.html | Our temporary multiplier/strain values are original balancing choices. |
| Bankai | Official Bleach Rebirth of Souls Ichigo Bankai page describes offensive strength and enhanced attacks. https://bleach-ros.bn-ent.net/character/index.php?chara=ichigo-kurosaki-bankai&s=09 | Universal card grants a bounded buff; a visual transformation requires a real adapter/assets. |
| PLUS ULTRA | Bandai Namco's Ultra Rumble guide describes its gauge and temporary comeback strengthening. https://en.bandainamcoent.eu/my-hero-academia/news/my-hero-ultra-rumble-open-beta-test-guide | Our HP threshold, hit shield and duration are not copied game values. |
| ZA WARUDO | Licensed JoJo fighting-game manual lists The World's time stop. https://static.jojowiki.com/images/0/0f/latest/20210515101755/JoJo%27s_Bizarre_Adventure_DC_English_Manual.pdf | Real scoped freeze is an engine task; short duration/damage cap are our rules. |
| Senzu Bean | Dragon Ball's official kanji feature describes restoration from Senzu Beans. https://en.dragon-ball-official.com/news/01_578.html | Modest interruptible heal, not a full canonical restoration or revival. |
| Pot of Greed | Konami's database specifies drawing two cards. https://www.db.yugioh-card.com/yugiohdb/card_search.action?cid=4844&ope=2&request_locale=en | Same recognizable draw identity with a mode-specific use limit and bounded queue. |

No content from those commercial games was downloaded/ripped for the kit. The
illustrations are original generated fan-art interpretations, not official art.
Art generation was explicitly requested by the owner through Higgsfield.

### Native AI evidence

Dolmexica source inspected locally at commit
`a6d63e9df096beb3baf4109d0ed9b44e68632895`:
https://github.com/CaptainDreamcast/DolmexicaInfinite/blob/a6d63e9df096beb3baf4109d0ed9b44e68632895/ai.cpp

`setRandomPlayerCommandActive` activates a character command; `updateAIMovement`
uses distance/state, `updateAIGuarding` attempts guards with a difficulty factor,
and `updateAICommands` schedules random command attempts. This establishes why
card interventions need a deliberate bridge rather than assuming one global
aggression toggle. Character CMD/CNS logic can implement its own additional AI.

No Legends AI adapter or new native card effect is implemented or verified by
this research/art delivery. That work is assigned through the Claude prompt.
