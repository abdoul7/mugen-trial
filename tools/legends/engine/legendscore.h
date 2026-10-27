// legendscore.h -- Legends mode rules, independent of the engine (docs/legends-design.md).
//
// Everything here is plain C++17 with no Dolmexica/prism dependency, so it can be unit
// tested on a PC (tools/legends/tests). The engine side (legendsmode.cpp) fills a
// CombatSnapshot every combat tick, calls Match::tick, and carries out the returned
// Actions (draw a sprite, deal card damage, heal). The AI and damage hooks query the
// ModifierRegistry through Match::profileFor / attackFactor / defenseFactor.
#pragma once

#include <array>
#include <cstdint>
#include <deque>
#include <map>
#include <string>
#include <vector>

namespace legends {

// ------------------------------------------------------------------ catalog
enum class Family { Resolve, SecretArts, Awakenings, PlotTwists };
enum class Rarity { Common, Rare, Epic, Legendary };
enum class EffectKind {
	None,           // disabled card: no implementation (never allowed on an enabled card)
	CoachProfile,   // Resolve: change the coach profile while attached
	EchoProjectile, // Secret Arts: card-owned projectile echo (one hit)
	Heal,           // Plot Twist: recover after a windup
	AttackBuff,     // Awakening: timed attack factor (+ optional strain)
	ComebackBuff,   // Awakening: low-HP attack factor + reduce the next N received hits
	BonusDraw,      // Plot Twist: add bonus draw tickets
};

const char* familyName(Family f);
const char* rarityName(Rarity r);

struct CardDef {
	std::string id;
	int revision = 1;
	Family family = Family::PlotTwists;
	Rarity rarity = Rarity::Common;
	std::string name, shortName, text;
	std::string flavor;            // one-line summary shown on the card face (the kit's short_text)
	bool enabled = false;          // authored + tested support exists
	std::string disabledReason;    // shown when !enabled
	EffectKind effect = EffectKind::Heal;
	int reservationTicks = 1;      // how long an armed card may wait for a legal opening
	int windupTicks = 0;           // committed, interruptible by a hit if `interruptible`
	bool interruptible = false;
	int durationTicks = 0;         // timed effects
	int perEncounter = 0;          // 0 = unlimited successful activations per coach
	int perFighter = 0;            // 0 = unlimited; else per squad member per encounter
	bool needsGrounded = false;    // legal opening: caster on the ground
	bool needsControl = false;     // legal opening: caster in control (not attacking/hit)
	float minHpFraction = 0, maxHpFraction = 1; // legal only within this caster HP range
	std::map<std::string, float> params;  // effect parameters (balance data)
	std::string capability;          // adapter capability needed ("" = none)
	std::vector<std::string> tags; // CoachProfile: tagged move opportunities to prefer

	float param(const std::string& k, float d = 0) const {
		auto it = params.find(k);
		return it == params.end() ? d : it->second;
	}
};

struct Catalog {
	int version = 0;
	std::array<int, 4> rarityWeights{{55, 30, 12, 3}};
	int hypeMax = 900, hypePerTick = 1, hypeEvent = 60, hypeEventCap = 120, hypeEventWindow = 60;
	int playCooldown = 90;
	std::vector<CardDef> cards;
	const CardDef* find(const std::string& id) const;
};

// Parses the text catalog written by tools/legends/make_legends.py. Returns "" on success,
// otherwise every problem found (unknown family/rarity/effect, duplicate ids, missing fields,
// no enabled common card).
std::string parseCatalog(const std::string& text, Catalog* out);
std::string validateCatalog(const Catalog& c);

// ------------------------------------------------------------------ character adapters
// Verified per-character facts (section 7): which of the character's own commands carry a tag
// (approach, poke, ...), and whether it runs its own scripted AI. No guessed state numbers.
struct Adapter {
	std::string id;
	std::string match;       // matched against the end of the character's .def path
	bool customAI = false;   // its CNS has its own AI: generic coaching may be ignored
	std::map<std::string, std::vector<std::string>> tags; // tag -> command names
};
std::string parseAdapters(const std::string& text, std::vector<Adapter>* out);
const Adapter* findAdapter(const std::vector<Adapter>& all, const std::string& defPath);

// ------------------------------------------------------------------ random
struct Rng { // xorshift64*: reproducible on every platform
	uint64_t s;
	explicit Rng(uint64_t seed = 1) : s(seed ? seed : 0x9E3779B97F4A7C15ull) {}
	uint64_t next() { s ^= s >> 12; s ^= s << 25; s ^= s >> 27; return s * 2685821657736338717ull; }
	int range(int lo, int hi) { return lo + int(next() % uint64_t(hi - lo + 1)); } // inclusive
};

// ------------------------------------------------------------------ per-tick world view
struct FighterView {
	bool alive = true;
	bool grounded = true;
	bool control = true;     // can act: not in hit/attack/recovery
	bool guarding = false;   // in a guard state
	bool gotHit = false;     // lost life to an opponent hit this tick
	bool knockedDown = false;// entered a knockdown this tick
	int life = 1000, lifeMax = 1000;
	float x = 0, y = 0;      // stage coordinates (320 space); y < 0 is up
	bool facingRight = true;
	float hpFraction() const { return lifeMax > 0 ? float(life) / lifeMax : 0; }
};

struct CombatSnapshot {
	int tick = 0;            // combat tick within the bout
	bool combatActive = true;// false during intro, pause, KO, transitions
	std::array<FighterView, 2> f;
};

// ------------------------------------------------------------------ outputs for the engine
enum class ActionKind { Damage, Heal, EchoSpawn, EchoMove, EchoEnd, Log };
struct Action {
	ActionKind kind;
	int side = 0;        // fighter acted on (Damage/Heal) or echo owner
	int amount = 0;      // life points
	int echoId = 0;
	float x = 0, y = 0;
	std::string text;    // Log text, or the card id for echoes
};

// What the AI hook may use for a side's fighter (docs/legends-design.md section 7)
struct CoachProfile {
	float approachDistance = 50, stopDistance = 30; // generic AI: move in beyond, stop within
	float guardBias = 0;                            // added to the guard chance, then clamped 15-85%
	float commandIntervalScale = 1;                 // < 1: tries moves more often
	float tagBias = 0;                              // share of command picks taken from tagged moves
	std::vector<std::string> preferredTags;         // e.g. approach, poke
	bool active = false;
};

// ------------------------------------------------------------------ cards in play
enum class CardState { Ready, Armed, Windup, Active, Discarded };
const char* stateName(CardState s);

struct CardInstance {
	int uid = 0;
	const CardDef* def = nullptr;
	CardState state = CardState::Ready;
	int armedTicks = 0;
	std::string reason;      // why an armed card is waiting, or why a play was rejected
	bool empty() const { return def == nullptr; }
};

struct Effect {          // a committed card's lasting part, identified by its source card uid
	int sourceUid = 0;
	const CardDef* def = nullptr;
	int side = 0;            // owner
	int target = 0;          // fighter side acted on
	int windupLeft = 0;
	int ticksLeft = 0;
	int hitsLeft = 0;        // ComebackBuff: received hits still reduced
	int strainCarry = 0;     // AttackBuff strain: fractional life carried between ticks (x1000)
	// echo projectile
	int echoId = 0;
	float ex = 0, ey = 0, evx = 0, travelled = 0;
	bool echoLive = false;
	bool done = false;
};

struct Coach {
	int side = 0;
	Rng rng;
	int hype = 0;
	std::deque<std::pair<int, int>> eventGains;  // (tick, amount) for the rolling bonus cap
	std::deque<char> tickets;                     // 'N' normal, 'B' bonus, FIFO
	std::array<CardInstance, 3> hand;
	int cooldown = 0;
	bool legendaryDrawn = false;
	std::map<std::string, int> uses;              // successful activations per card id this encounter
	int drawIndex = 0;
	int cardsDrawn = 0, cardsPlayed = 0;
	std::vector<std::string> bannedCards; // test-only per-coach draw exclusions, set before the deal
	std::vector<std::string> playedIds;
	// CPU coach
	bool isCpu = false;
	int nextThink = 0;
	int thinkDelay = 0;
	int armedSlot = -1;                           // the one reservation per coach
	bool hasFreeSlot() const;
	int freeSlot() const;
	int handCount() const;
	bool holds(const std::string& id) const;
};

// ------------------------------------------------------------------ squads and relay
struct SquadMember {
	std::string path;        // character .def
	std::string name;        // display name
	float hpFraction = 1;
	bool eliminated = false;
	std::string resolveId;   // attached Resolve ("" = none)
	bool hasAdapter = false; // a verified CharacterAdapter exists
};

enum class BoutEnd { None, KO, Timeout };
struct BoutResult {
	BoutEnd how = BoutEnd::None;
	std::array<bool, 2> lost{{false, false}}; // which side's fighter is eliminated
	std::array<float, 2> hpFraction{{1, 1}};
};

// Decides a bout from the two fighters' final state (design section 3): a KO'd fighter is
// eliminated (both on a double KO); on timeout the lower HP fraction loses, an exact tie
// eliminates both.
BoutResult judgeBout(const FighterView& a, const FighterView& b, bool timedOut);

struct Squad {
	std::array<SquadMember, 3> members;
	int active = 0;          // index of the fighter in the current bout
	int remaining() const;
	int nextAlive(int from) const;
};

// ------------------------------------------------------------------ the match
class Match {
public:
	// capability check: can this side's current fighter use the card's `requires`?
	Match(const Catalog* catalog, uint64_t seed);

	const Catalog* catalog;
	uint64_t seed;
	std::array<Coach, 2> coach;
	std::array<Squad, 2> squad;
	int boutNumber = 0;      // 1-based once started
	int boutTickLimit = 90 * 60;
	std::vector<Effect> effects;
	int nextUid = 1, nextEchoId = 1;
	int lastTieBreak = -1;   // side that won the last simultaneous-intent tie
	std::vector<std::string> log;

	// setup
	void setCpu(int side, bool cpu);
	std::vector<const CardDef*> eligible(int side, bool openingCommonRare, Family* onlyFamily) const;
	const CardDef* drawCard(int side, bool openingCommonRare, Family* onlyFamily, const char* why);
	void dealOpening(int side);              // one Resolve + two Common/Rare, no duplicate ids
	bool attachResolve(int side, int slot, int member); // opening screen: equip from hand
	void cpuChooseOpening(int side);

	// relay
	void startBout();                         // called before each bout loads
	void endBout(const BoutResult& r);        // apply eliminations, HP carryover, cleanup
	bool over() const;
	int winner() const;                       // 0/1, or -1 = draw

	// combat
	std::vector<Action> tick(const CombatSnapshot& s);
	std::string requestPlay(int side, int slot, const CombatSnapshot& s); // "" = armed/played
	void discard(int side, int slot);

	// hooks
	CoachProfile profileFor(int side) const;
	float attackFactor(int side) const;
	float defenseFactor(int side, bool consumeHit);
	int awakeningTicksLeft(int side) const;
	std::string awakeningName(int side) const;

	void addHypeEvent(int side, int tick);    // meaningful exchange (deduplicated by caller)
	void logf(const char* fmt, ...);

private:
	void deliverTickets(int side);
	void gainHype(int side, int amount);
	std::string legalNow(const Coach& c, const CardDef* d, const CombatSnapshot& s) const;
	void commit(int side, int slot, const CombatSnapshot& s, std::vector<Action>* out);
	void runEffects(const CombatSnapshot& s, std::vector<Action>* out);
	void cpuThink(int side, const CombatSnapshot& s);
	void clearEffects(bool boutEnded);
	bool capabilityOk(int side, const CardDef* d) const;
};

} // namespace legends
