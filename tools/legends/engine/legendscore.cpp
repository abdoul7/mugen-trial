// legendscore.cpp -- see legendscore.h. Section numbers refer to docs/legends-design.md.
#include "legendscore.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <sstream>

namespace legends {

const char* familyName(Family f) {
	switch (f) {
	case Family::Resolve: return "RESOLVE";
	case Family::SecretArts: return "SECRET ARTS";
	case Family::Awakenings: return "AWAKENING";
	default: return "PLOT TWIST";
	}
}

const char* rarityName(Rarity r) {
	switch (r) {
	case Rarity::Common: return "C";
	case Rarity::Rare: return "R";
	case Rarity::Epic: return "E";
	default: return "L";
	}
}

const char* stateName(CardState s) {
	switch (s) {
	case CardState::Ready: return "READY";
	case CardState::Armed: return "ARMED";
	case CardState::Windup: return "WINDUP";
	case CardState::Active: return "ACTIVE";
	default: return "DISCARD";
	}
}

const CardDef* Catalog::find(const std::string& id) const {
	for (auto& c : cards) if (c.id == id) return &c;
	return nullptr;
}

// ------------------------------------------------------------------ catalog text
static std::string trim(const std::string& s) {
	size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
	return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

static std::vector<std::string> splitList(const std::string& s) {
	std::vector<std::string> out;
	std::stringstream ss(s);
	std::string item;
	while (std::getline(ss, item, ',')) {
		item = trim(item);
		if (!item.empty()) out.push_back(item);
	}
	return out;
}

static bool parseFamily(const std::string& v, Family* f) {
	if (v == "resolve") *f = Family::Resolve;
	else if (v == "secret_arts") *f = Family::SecretArts;
	else if (v == "awakenings") *f = Family::Awakenings;
	else if (v == "plot_twists") *f = Family::PlotTwists;
	else return false;
	return true;
}

static bool parseRarity(const std::string& v, Rarity* r) {
	if (v == "common") *r = Rarity::Common;
	else if (v == "rare") *r = Rarity::Rare;
	else if (v == "epic") *r = Rarity::Epic;
	else if (v == "legendary") *r = Rarity::Legendary;
	else return false;
	return true;
}

static bool parseEffect(const std::string& v, EffectKind* e) {
	if (v == "none") *e = EffectKind::None;
	else if (v == "coach_profile") *e = EffectKind::CoachProfile;
	else if (v == "echo_projectile") *e = EffectKind::EchoProjectile;
	else if (v == "heal") *e = EffectKind::Heal;
	else if (v == "attack_buff") *e = EffectKind::AttackBuff;
	else if (v == "comeback_buff") *e = EffectKind::ComebackBuff;
	else if (v == "bonus_draw") *e = EffectKind::BonusDraw;
	else return false;
	return true;
}

std::string parseCatalog(const std::string& text, Catalog* out) {
	Catalog c;
	std::string errors;
	std::stringstream in(text);
	std::string line, section;
	CardDef* card = nullptr;
	std::set<std::string> ids;
	int lineNo = 0;
	auto err = [&](const std::string& m) { errors += "line " + std::to_string(lineNo) + ": " + m + "\n"; };
	while (std::getline(in, line)) {
		lineNo++;
		line = trim(line);
		if (line.empty() || line[0] == ';' || line[0] == '#') continue;
		if (line[0] == '[') {
			const auto close = line.find(']');
			section = trim(line.substr(1, close == std::string::npos ? std::string::npos : close - 1));
			card = nullptr;
			if (section.rfind("card ", 0) == 0) {
				CardDef d;
				d.id = trim(section.substr(5));
				if (!ids.insert(d.id).second) err("duplicate card id " + d.id);
				c.cards.push_back(d);
				card = &c.cards.back();
			}
			else if (section != "legends") err("unknown section [" + section + "]");
			continue;
		}
		const auto eq = line.find('=');
		if (eq == std::string::npos) { err("expected key = value"); continue; }
		const auto k = trim(line.substr(0, eq)), v = trim(line.substr(eq + 1));
		const auto num = [&]() { return float(atof(v.c_str())); };
		if (!card) {
			if (k == "version") c.version = atoi(v.c_str());
			else if (k == "rarity.weights") {
				auto w = splitList(v);
				if (w.size() != 4) err("rarity.weights needs 4 values");
				else for (int i = 0; i < 4; i++) c.rarityWeights[i] = atoi(w[i].c_str());
			}
			else if (k == "hype.max") c.hypeMax = atoi(v.c_str());
			else if (k == "hype.tick") c.hypePerTick = atoi(v.c_str());
			else if (k == "hype.event") c.hypeEvent = atoi(v.c_str());
			else if (k == "hype.event.cap") c.hypeEventCap = atoi(v.c_str());
			else if (k == "hype.event.window") c.hypeEventWindow = atoi(v.c_str());
			else if (k == "play.cooldown") c.playCooldown = atoi(v.c_str());
			else err("unknown key " + k);
			continue;
		}
		if (k == "revision") card->revision = atoi(v.c_str());
		else if (k == "family") { if (!parseFamily(v, &card->family)) err("unknown family " + v); }
		else if (k == "rarity") { if (!parseRarity(v, &card->rarity)) err("unknown rarity " + v); }
		else if (k == "effect") { if (!parseEffect(v, &card->effect)) err("unknown effect " + v); }
		else if (k == "name") card->name = v;
		else if (k == "short") card->shortName = v;
		else if (k == "text") card->text = v;
		else if (k == "flavor") card->flavor = v;
		else if (k == "per.fighter") card->perFighter = atoi(v.c_str());
		else if (k == "enabled") card->enabled = atoi(v.c_str()) != 0;
		else if (k == "disabled.reason") card->disabledReason = v;
		else if (k == "reservation") card->reservationTicks = atoi(v.c_str());
		else if (k == "windup") card->windupTicks = atoi(v.c_str());
		else if (k == "interruptible") card->interruptible = atoi(v.c_str()) != 0;
		else if (k == "duration") card->durationTicks = atoi(v.c_str());
		else if (k == "per.encounter") card->perEncounter = atoi(v.c_str());
		else if (k == "needs.grounded") card->needsGrounded = atoi(v.c_str()) != 0;
		else if (k == "needs.control") card->needsControl = atoi(v.c_str()) != 0;
		else if (k == "hp.min") card->minHpFraction = num();
		else if (k == "hp.max") card->maxHpFraction = num();
		else if (k == "requires") card->capability = v;
		else if (k == "tags") card->tags = splitList(v);
		else if (k.rfind("param.", 0) == 0) card->params[k.substr(6)] = num();
		else err("unknown key " + k + " in card " + card->id);
	}
	if (errors.empty()) errors = validateCatalog(c);
	if (errors.empty()) *out = c;
	return errors;
}

std::string validateCatalog(const Catalog& c) {
	std::string e;
	bool safeCommon = false;
	std::set<std::string> ids;
	for (auto& d : c.cards) {
		if (d.id.empty()) e += "card without id\n";
		if (!ids.insert(d.id).second) e += "duplicate card id " + d.id + "\n";
		if (d.name.empty() || d.shortName.empty()) e += d.id + ": name and short are required\n";
		if (!d.enabled && d.disabledReason.empty()) e += d.id + ": disabled cards need disabled.reason\n";
		if (d.reservationTicks < 1 || d.reservationTicks > 60) e += d.id + ": reservation must be 1..60 ticks\n";
		if (d.windupTicks < 0 || d.durationTicks < 0) e += d.id + ": negative timing\n";
		if (d.enabled && d.effect == EffectKind::None) e += d.id + ": enabled card without an effect\n";
		if (d.enabled && d.rarity == Rarity::Common) safeCommon = true;
	}
	if (c.hypeMax <= 0 || c.playCooldown < 0) e += "bad hype/cooldown settings\n";
	if (!safeCommon) e += "no enabled Common card: Legends cannot start (section 5)\n";
	return e;
}

// ------------------------------------------------------------------ adapters
std::string parseAdapters(const std::string& text, std::vector<Adapter>* out) {
	std::vector<Adapter> all;
	std::string errors, line;
	std::stringstream in(text);
	int lineNo = 0;
	while (std::getline(in, line)) {
		lineNo++;
		line = trim(line);
		if (line.empty() || line[0] == ';' || line[0] == '#') continue;
		if (line[0] == '[') {
			const auto close = line.find(']');
			const auto sec = trim(line.substr(1, close == std::string::npos ? std::string::npos : close - 1));
			if (sec.rfind("adapter ", 0) != 0) { errors += "line " + std::to_string(lineNo) + ": unknown section\n"; continue; }
			Adapter a;
			a.id = trim(sec.substr(8));
			all.push_back(a);
			continue;
		}
		const auto eq = line.find('=');
		if (eq == std::string::npos || all.empty()) { errors += "line " + std::to_string(lineNo) + ": expected key = value in an [adapter]\n"; continue; }
		const auto k = trim(line.substr(0, eq)), v = trim(line.substr(eq + 1));
		auto& a = all.back();
		if (k == "match") a.match = v;
		else if (k == "custom_ai") a.customAI = atoi(v.c_str()) != 0;
		else if (k.rfind("tag.", 0) == 0) a.tags[k.substr(4)] = splitList(v);
		else errors += "line " + std::to_string(lineNo) + ": unknown key " + k + "\n";
	}
	for (auto& a : all) if (a.match.empty()) errors += "adapter " + a.id + " has no match\n";
	if (errors.empty()) *out = all;
	return errors;
}

const Adapter* findAdapter(const std::vector<Adapter>& all, const std::string& defPath) {
	std::string p = defPath;
	for (auto& ch : p) ch = char(tolower(ch));
	for (auto& a : all) {
		std::string m = a.match;
		for (auto& ch : m) ch = char(tolower(ch));
		if (p.size() >= m.size() && p.compare(p.size() - m.size(), m.size(), m) == 0) return &a;
	}
	return nullptr;
}

// ------------------------------------------------------------------ squads
int Squad::remaining() const {
	int n = 0;
	for (auto& m : members) n += m.eliminated ? 0 : 1;
	return n;
}

int Squad::nextAlive(int from) const {
	for (int i = from; i < 3; i++) if (!members[i].eliminated) return i;
	return -1;
}

BoutResult judgeBout(const FighterView& a, const FighterView& b, bool timedOut) {
	BoutResult r;
	r.hpFraction = {{a.alive ? a.hpFraction() : 0, b.alive ? b.hpFraction() : 0}};
	r.lost = {{!a.alive, !b.alive}};
	if (!a.alive || !b.alive) {
		r.how = BoutEnd::KO;
		return r;
	}
	if (!timedOut) return r;
	r.how = BoutEnd::Timeout;
	const float fa = a.hpFraction(), fb = b.hpFraction();
	if (fa == fb) r.lost = {{true, true}};   // exact tie eliminates both
	else if (fa < fb) r.lost[0] = true;
	else r.lost[1] = true;
	return r;
}

// ------------------------------------------------------------------ coach helpers
bool Coach::hasFreeSlot() const { return freeSlot() >= 0; }
int Coach::freeSlot() const {
	for (int i = 0; i < 3; i++) if (hand[i].empty()) return i;
	return -1;
}
int Coach::handCount() const {
	int n = 0;
	for (auto& h : hand) n += h.empty() ? 0 : 1;
	return n;
}
bool Coach::holds(const std::string& id) const {
	for (auto& h : hand) if (!h.empty() && h.def->id == id) return true;
	return false;
}

// ------------------------------------------------------------------ match
Match::Match(const Catalog* cat, uint64_t s) : catalog(cat), seed(s) {
	for (int i = 0; i < 2; i++) {
		coach[i].side = i;
		coach[i].rng = Rng(s * 2 + 1 + uint64_t(i) * 0x5851F42D4C957F2Dull);
	}
	lastTieBreak = int(s & 1);
	logf("match seed %llu catalog v%d", (unsigned long long)s, cat->version);
}

void Match::logf(const char* fmt, ...) {
	char b[300];
	va_list a;
	va_start(a, fmt);
	vsnprintf(b, sizeof(b), fmt, a);
	va_end(a);
	log.push_back(b);
}

void Match::setCpu(int side, bool cpu) { coach[side].isCpu = cpu; }

bool Match::capabilityOk(int side, const CardDef* d) const {
	if (d->capability.empty()) return true;
	const auto& sq = squad[side];
	// "adapter": the current fighter needs a verified CharacterAdapter (section 7)
	if (d->capability == "adapter") return sq.members[sq.active].hasAdapter;
	return false; // unknown capability: never eligible
}

std::vector<const CardDef*> Match::eligible(int side, bool openingCommonRare, Family* onlyFamily) const {
	std::vector<const CardDef*> out;
	const auto& c = coach[side];
	const auto& member = squad[side].members[squad[side].active];
	for (auto& d : catalog->cards) {
		if (!d.enabled) continue;                       // no safe implementation: never drawn
		if (onlyFamily && d.family != *onlyFamily) continue;
		if (openingCommonRare && d.rarity != Rarity::Common && d.rarity != Rarity::Rare) continue;
		if (d.rarity == Rarity::Legendary && c.legendaryDrawn) continue;
		if (c.holds(d.id)) continue;                    // no duplicate id in hand
		if (d.family == Family::Resolve && member.resolveId == d.id) continue;
		if (d.perEncounter > 0) {
			auto it = c.uses.find(d.id);
			if (it != c.uses.end() && it->second >= d.perEncounter) continue;
		}
		if (d.perFighter > 0) {
			auto it = c.uses.find(d.id + "@" + std::to_string(squad[side].active));
			if (it != c.uses.end() && it->second >= d.perFighter) continue;
		}
		if (!capabilityOk(side, &d)) continue;
		out.push_back(&d);
	}
	return out;
}

const CardDef* Match::drawCard(int side, bool openingCommonRare, Family* onlyFamily, const char* why) {
	auto& c = coach[side];
	const int slot = c.freeSlot();
	if (slot < 0) return nullptr;
	const auto pool = eligible(side, openingCommonRare, onlyFamily);
	// pick a rarity among the nonempty buckets (renormalised), then a card uniformly in it
	std::array<std::vector<const CardDef*>, 4> bucket;
	for (auto* d : pool) bucket[int(d->rarity)].push_back(d);
	int total = 0;
	for (int r = 0; r < 4; r++) if (!bucket[r].empty()) total += catalog->rarityWeights[r];
	if (total <= 0) {
		logf("draw side %d: no eligible card (%s)", side, why);
		return nullptr;
	}
	int roll = c.rng.range(0, total - 1), r = 0;
	for (; r < 4; r++) {
		if (bucket[r].empty()) continue;
		if (roll < catalog->rarityWeights[r]) break;
		roll -= catalog->rarityWeights[r];
	}
	const CardDef* d = bucket[r][c.rng.range(0, int(bucket[r].size()) - 1)];
	c.hand[slot].uid = nextUid++;
	c.hand[slot].def = d;
	c.hand[slot].state = CardState::Ready;
	c.hand[slot].reason.clear();
	if (d->rarity == Rarity::Legendary) c.legendaryDrawn = true; // stays removed even if discarded
	c.drawIndex++;
	c.cardsDrawn++;
	logf("draw side %d #%d %s (%s, %s) %s", side, c.drawIndex, d->id.c_str(), familyName(d->family), rarityName(d->rarity), why);
	return d;
}

void Match::dealOpening(int side) {
	Family f = Family::Resolve;
	if (!drawCard(side, false, &f, "opening resolve")) logf("side %d: no enabled Resolve for the opening", side);
	while (coach[side].handCount() < 3) {
		if (!drawCard(side, true, nullptr, "opening")) break;
	}
}

bool Match::attachResolve(int side, int slot, int member) {
	auto& c = coach[side];
	if (slot < 0 || slot > 2 || c.hand[slot].empty() || c.hand[slot].def->family != Family::Resolve) return false;
	if (member < 0 || member > 2 || squad[side].members[member].eliminated) return false;
	squad[side].members[member].resolveId = c.hand[slot].def->id;
	logf("side %d attaches %s to %s", side, c.hand[slot].def->id.c_str(), squad[side].members[member].name.c_str());
	c.playedIds.push_back(c.hand[slot].def->id);
	c.cardsPlayed++;
	c.hand[slot] = CardInstance();
	return true;
}

void Match::cpuChooseOpening(int side) {
	for (int s = 0; s < 3; s++) {
		if (!coach[side].hand[s].empty() && coach[side].hand[s].def->family == Family::Resolve) {
			attachResolve(side, s, squad[side].active);
			return;
		}
	}
}

// ------------------------------------------------------------------ relay
void Match::startBout() {
	boutNumber++;
	for (auto& c : coach) {
		c.armedSlot = -1;
		for (auto& h : c.hand) if (!h.empty()) { h.state = CardState::Ready; h.armedTicks = 0; h.reason.clear(); }
		c.cooldown = 0;
		c.nextThink = 0;
		c.thinkDelay = 0;
		c.eventGains.clear();
	}
	effects.clear();
	logf("bout %d: %s vs %s", boutNumber, squad[0].members[squad[0].active].name.c_str(), squad[1].members[squad[1].active].name.c_str());
}

void Match::clearEffects(bool boutEnded) {
	for (auto& e : effects) {
		if (!e.done) logf("effect %s (side %d) cleaned up%s", e.def->id.c_str(), e.side, boutEnded ? " at bout end" : "");
	}
	effects.clear();
}

void Match::endBout(const BoutResult& r) {
	clearEffects(true);   // temporary effects expire at the end of each bout
	for (int s = 0; s < 2; s++) {
		auto& c = coach[s];
		if (c.armedSlot >= 0) { c.hand[c.armedSlot].state = CardState::Ready; c.armedSlot = -1; } // never carried into the next bout
		auto& m = squad[s].members[squad[s].active];
		m.hpFraction = std::max(0.0f, std::min(1.0f, r.hpFraction[s]));
		if (r.lost[s]) {
			m.eliminated = true;
			m.hpFraction = 0;
			if (!m.resolveId.empty()) logf("side %d: %s leaves with %s", s, m.name.c_str(), m.resolveId.c_str());
			m.resolveId.clear();
			const int n = squad[s].nextAlive(squad[s].active + 1);
			squad[s].active = n >= 0 ? n : squad[s].active;
		}
	}
	logf("bout %d ends (%s): side0 %s %.2f, side1 %s %.2f", boutNumber, r.how == BoutEnd::KO ? "KO" : "timeout",
		r.lost[0] ? "out" : "stays", r.hpFraction[0], r.lost[1] ? "out" : "stays", r.hpFraction[1]);
}

bool Match::over() const { return squad[0].remaining() == 0 || squad[1].remaining() == 0; }

int Match::winner() const {
	const int a = squad[0].remaining(), b = squad[1].remaining();
	if (a == 0 && b == 0) return -1;
	if (b == 0) return 0;
	if (a == 0) return 1;
	return -2; // not over
}

// ------------------------------------------------------------------ hype and draws
void Match::gainHype(int side, int amount) {
	auto& c = coach[side];
	c.hype += amount;
	if (c.hype < catalog->hypeMax) return;
	const bool normalWaiting = std::find(c.tickets.begin(), c.tickets.end(), 'N') != c.tickets.end();
	if (!normalWaiting && c.tickets.size() < 3) {
		c.hype -= catalog->hypeMax;
		c.tickets.push_back('N');
		logf("side %d: hype full, draw ticket", side);
	}
	else c.hype = catalog->hypeMax; // capped until the waiting ticket is delivered
}

void Match::addHypeEvent(int side, int tick) {
	auto& c = coach[side];
	while (!c.eventGains.empty() && tick - c.eventGains.front().first >= catalog->hypeEventWindow) c.eventGains.pop_front();
	int recent = 0;
	for (auto& g : c.eventGains) recent += g.second;
	const int gain = std::min(catalog->hypeEvent, catalog->hypeEventCap - recent);
	if (gain <= 0) return;
	c.eventGains.push_back({tick, gain});
	gainHype(side, gain);
}

void Match::deliverTickets(int side) {
	auto& c = coach[side];
	while (!c.tickets.empty() && c.hasFreeSlot()) {
		const char t = c.tickets.front();
		if (!drawCard(side, false, nullptr, t == 'N' ? "hype ticket" : "bonus ticket")) break; // waits until a card is eligible
		c.tickets.pop_front();
	}
}

// ------------------------------------------------------------------ playing cards
static float distanceX(const CombatSnapshot& s) { return std::fabs(s.f[0].x - s.f[1].x); }

std::string Match::legalNow(const Coach& c, const CardDef* d, const CombatSnapshot& s) const {
	const auto& me = s.f[c.side];
	if (!s.combatActive) return "PAUSED";
	if (!me.alive || !s.f[1 - c.side].alive) return "KO";
	if (d->needsGrounded && !me.grounded) return "WAIT: GROUND";
	if (d->needsControl && !me.control) return "WAIT: OPENING";
	if (me.hpFraction() < d->minHpFraction || me.hpFraction() > d->maxHpFraction) return "WAIT: HP";
	return "";
}

std::string Match::requestPlay(int side, int slot, const CombatSnapshot& s) {
	auto& c = coach[side];
	if (slot < 0 || slot > 2 || c.hand[slot].empty()) return "EMPTY";
	auto& card = c.hand[slot];
	const auto* d = card.def;
	auto reject = [&](const char* why) {
		card.reason = why;
		logf("side %d play %s rejected: %s", side, d->id.c_str(), why);
		return std::string(why);
	};
	if (card.state != CardState::Ready) return reject("NOT READY");
	if (!s.combatActive) return reject("PAUSED");
	if (!s.f[side].alive) return reject("KO");
	if (c.cooldown > 0) return reject("COOLDOWN");
	if (c.armedSlot >= 0) return reject("ONE AT A TIME");
	if (!capabilityOk(side, d)) return reject("UNSUPPORTED");
	if (d->perEncounter > 0 && c.uses[d->id] >= d->perEncounter) return reject("USED");
	if (d->perFighter > 0 && c.uses[d->id + "@" + std::to_string(squad[side].active)] >= d->perFighter) return reject("USED BY THIS FIGHTER");
	if (d->family == Family::Awakenings) {
		for (auto& e : effects) if (!e.done && e.side == side && e.def->family == Family::Awakenings) return reject("AWAKENING ACTIVE");
	}
	if (d->family == Family::Resolve && squad[side].members[squad[side].active].resolveId == d->id) return reject("EQUIPPED");
	if (d->effect == EffectKind::BonusDraw && c.tickets.size() >= 3) return reject("QUEUE FULL");
	if (d->effect == EffectKind::Heal && s.f[side].life >= s.f[side].lifeMax) return reject("FULL HP");
	card.state = CardState::Armed;
	card.armedTicks = 0;
	card.reason = legalNow(c, d, s);
	c.armedSlot = slot;
	logf("side %d arms %s%s%s", side, d->id.c_str(), card.reason.empty() ? "" : ": ", card.reason.c_str());
	return "";
}

void Match::discard(int side, int slot) {
	auto& c = coach[side];
	if (slot < 0 || slot > 2 || c.hand[slot].empty() || c.hand[slot].state != CardState::Ready || c.cooldown > 0) return;
	logf("side %d discards %s", side, c.hand[slot].def->id.c_str());
	c.hand[slot] = CardInstance();
	c.cooldown = catalog->playCooldown; // same shared cooldown, no Hype
}

void Match::commit(int side, int slot, const CombatSnapshot& s, std::vector<Action>* out) {
	auto& c = coach[side];
	const CardDef* d = c.hand[slot].def;
	const int uid = c.hand[slot].uid;
	c.hand[slot] = CardInstance();   // consumed: a draw may fill the slot from now on
	c.armedSlot = -1;
	c.cooldown = catalog->playCooldown;
	c.uses[d->id]++;
	c.uses[d->id + "@" + std::to_string(squad[side].active)]++;
	c.cardsPlayed++;
	c.playedIds.push_back(d->id);
	logf("tick %d side %d commits %s", s.tick, side, d->id.c_str());
	out->push_back({ActionKind::Log, side, 0, 0, 0, 0, d->id});
	if (d->effect == EffectKind::CoachProfile) {
		auto& m = squad[side].members[squad[side].active];
		logf("side %d: %s Resolve %s -> %s", side, m.name.c_str(), m.resolveId.empty() ? "none" : m.resolveId.c_str(), d->id.c_str());
		m.resolveId = d->id;   // atomic replacement: profiles are derived from the attached id
		return;
	}
	if (d->effect == EffectKind::BonusDraw) {
		const int want = int(d->param("draws", 2));
		int added = 0;
		for (int i = 0; i < want; i++) {
			const int bonus = int(std::count(c.tickets.begin(), c.tickets.end(), 'B'));
			if (c.tickets.size() >= 3 || bonus >= 2) break;
			c.tickets.push_back('B');
			added++;
		}
		logf("side %d: %d bonus ticket(s), %d lost to the queue limit", side, added, want - added);
		return;
	}
	Effect e;
	e.sourceUid = uid;
	e.def = d;
	e.side = side;
	e.target = d->family == Family::SecretArts ? 1 - side : side;
	e.windupLeft = d->windupTicks;
	e.ticksLeft = d->durationTicks;
	e.hitsLeft = int(d->param("hits", 0));
	effects.push_back(e);
}

void Match::runEffects(const CombatSnapshot& s, std::vector<Action>* out) {
	for (auto& e : effects) {
		if (e.done) continue;
		const auto& me = s.f[e.side];
		const auto& foe = s.f[1 - e.side];
		if (!me.alive || (!foe.alive && e.def->family == Family::SecretArts)) {
			if (e.echoLive) out->push_back({ActionKind::EchoEnd, e.side, 0, e.echoId});
			e.done = true;
			continue;
		}
		if (e.windupLeft > 0) {
			if (e.def->interruptible && me.gotHit) {   // the deliberate risk: card and cost are lost
				logf("tick %d side %d: %s interrupted during windup", s.tick, e.side, e.def->id.c_str());
				out->push_back({ActionKind::Log, e.side, 0, 0, 0, 0, "interrupted"});
				e.done = true;
				continue;
			}
			if (--e.windupLeft > 0) continue;
			// windup finished: the effect starts now (timed effects count from here)
			if (e.def->effect == EffectKind::Heal) {
				const int amount = std::min(int(std::lround(e.def->param("heal", 0.12f) * me.lifeMax)), me.lifeMax - me.life);
				if (amount > 0) out->push_back({ActionKind::Heal, e.side, amount});
				logf("tick %d side %d heals %d", s.tick, e.side, amount);
				e.done = true;
				continue;
			}
			if (e.def->effect == EffectKind::EchoProjectile) {
				const float dir = foe.x >= me.x ? 1.f : -1.f;
				e.echoId = nextEchoId++;
				e.ex = me.x + dir * e.def->param("spawn.x", 20);
				e.ey = me.y + e.def->param("spawn.y", -40);
				e.evx = dir * e.def->param("speed", 5);
				e.echoLive = true;
				out->push_back({ActionKind::EchoSpawn, e.side, 0, e.echoId, e.ex, e.ey, e.def->id});
				continue;
			}
		}
		switch (e.def->effect) {
		case EffectKind::EchoProjectile: {
			e.ex += e.evx;
			e.travelled += std::fabs(e.evx);
			const bool contact = std::fabs(e.ex - foe.x) < e.def->param("hit.w", 16) && std::fabs((foe.y - 40) - e.ey) < e.def->param("hit.h", 50);
			if (contact) {
				if (foe.guarding) {
					logf("tick %d side %d: %s blocked", s.tick, e.side, e.def->id.c_str());
					out->push_back({ActionKind::Log, e.side, 0, 0, 0, 0, "blocked"});
				}
				else {
					const int dmg = int(std::lround(e.def->param("damage", 0.06f) * foe.lifeMax));
					out->push_back({ActionKind::Damage, 1 - e.side, dmg, e.echoId, e.ex, e.ey, e.def->id});
					logf("tick %d side %d: %s hits for %d", s.tick, e.side, e.def->id.c_str(), dmg);
				}
				out->push_back({ActionKind::EchoEnd, e.side, 0, e.echoId, e.ex, e.ey});
				e.done = true;
			}
			else if (e.travelled >= e.def->param("range", 240)) {
				logf("tick %d side %d: %s missed", s.tick, e.side, e.def->id.c_str());
				out->push_back({ActionKind::EchoEnd, e.side, 0, e.echoId, e.ex, e.ey});
				e.done = true;
			}
			else out->push_back({ActionKind::EchoMove, e.side, 0, e.echoId, e.ex, e.ey});
			break;
		}
		case EffectKind::AttackBuff:
		case EffectKind::ComebackBuff: {
			const float strain = e.def->param("strain", 0);   // fraction of max HP per second
			if (strain > 0) {
				e.strainCarry += int(std::lround(strain * me.lifeMax * 1000 / 60));
				const int whole = std::min(e.strainCarry / 1000, me.life - 1); // strain never KOs the caster
				e.strainCarry %= 1000;
				if (whole > 0) out->push_back({ActionKind::Damage, e.side, whole, 0, 0, 0, "strain"});
			}
			if (--e.ticksLeft <= 0) {
				logf("tick %d side %d: %s ends", s.tick, e.side, e.def->id.c_str());
				e.done = true;
			}
			break;
		}
		default:
			e.done = true;
		}
	}
	effects.erase(std::remove_if(effects.begin(), effects.end(), [](const Effect& e) { return e.done; }), effects.end());
}

// ------------------------------------------------------------------ CPU coach
// Same hand, odds, cooldowns and checks as the human; decides every 15 ticks plus a seeded
// 6-12 tick reaction delay, from public state and its own cards only (section 7).
void Match::cpuThink(int side, const CombatSnapshot& s) {
	auto& c = coach[side];
	if (c.thinkDelay > 0) {
		if (--c.thinkDelay > 0) return;
		const auto& me = s.f[side];
		const float dist = distanceX(s);
		int best = -1;
		for (int i = 0; i < 3 && best < 0; i++) {
			if (c.hand[i].empty() || c.hand[i].state != CardState::Ready) continue;
			const auto* d = c.hand[i].def;
			bool want = false;
			switch (d->effect) {
			case EffectKind::Heal: want = me.hpFraction() < 0.5f && dist > 70; break;
			case EffectKind::AttackBuff: want = dist < 90 && me.hpFraction() > 0.3f; break;
			case EffectKind::ComebackBuff: want = me.hpFraction() < d->maxHpFraction; break;
			case EffectKind::EchoProjectile: want = dist > 40 && dist < d->param("range", 240) * 0.8f; break;
			case EffectKind::BonusDraw: want = c.handCount() <= 2; break;
			case EffectKind::CoachProfile: want = squad[side].members[squad[side].active].resolveId.empty(); break;
			case EffectKind::None: break;
			}
			if (want) best = i;
		}
		if (best >= 0) requestPlay(side, best, s);
		return;
	}
	if (s.tick >= c.nextThink) {
		c.nextThink = s.tick + 15;
		if (c.armedSlot < 0 && c.cooldown == 0) c.thinkDelay = c.rng.range(6, 12);
	}
}

// ------------------------------------------------------------------ one combat tick
std::vector<Action> Match::tick(const CombatSnapshot& s) {
	std::vector<Action> out;
	if (!s.combatActive) return out;   // hype, cooldowns, reservations and effects all pause
	for (int side = 0; side < 2; side++) {
		gainHype(side, catalog->hypePerTick);
		if (s.f[1 - side].knockedDown) addHypeEvent(side, s.tick); // knockdown caused
	}
	for (int side = 0; side < 2; side++) deliverTickets(side);
	for (int side = 0; side < 2; side++) if (coach[side].isCpu) cpuThink(side, s);

	// armed cards: both coaches' intents are collected first, then committed in an
	// alternating order (seeded start), so neither side has a fixed first-move advantage
	std::vector<int> ready;
	for (int side = 0; side < 2; side++) {
		auto& c = coach[side];
		if (c.armedSlot < 0) continue;
		auto& card = c.hand[c.armedSlot];
		card.reason = legalNow(c, card.def, s);
		if (card.reason.empty()) ready.push_back(side);
		else if (++card.armedTicks > card.def->reservationTicks) {
			logf("tick %d side %d: %s expired (%s), back to hand", s.tick, side, card.def->id.c_str(), card.reason.c_str());
			card.state = CardState::Ready;
			card.reason = "EXPIRED";
			c.armedSlot = -1;
		}
	}
	if (ready.size() == 2) {
		const int first = 1 - lastTieBreak;
		lastTieBreak = first;
		logf("tick %d: simultaneous plays, side %d first", s.tick, first);
		ready = {first, 1 - first};
	}
	for (int side : ready) commit(side, coach[side].armedSlot, s, &out);

	for (auto& c : coach) if (c.cooldown > 0) c.cooldown--;
	runEffects(s, &out);
	for (int side = 0; side < 2; side++) deliverTickets(side);
	return out;
}

// ------------------------------------------------------------------ hooks
CoachProfile Match::profileFor(int side) const {
	CoachProfile p;
	const auto& m = squad[side].members[squad[side].active];
	if (!m.resolveId.empty()) {
		if (const auto* d = catalog->find(m.resolveId)) {
			p.active = true;
			p.approachDistance = d->param("approach", p.approachDistance);
			p.stopDistance = d->param("stop", p.stopDistance);
			p.guardBias = d->param("guard", 0);
			p.commandIntervalScale = d->param("interval", 1);
			// tagged moves only steer fighters with a verified adapter
			p.tagBias = m.hasAdapter ? d->param("tag.bias", 0) : 0;
			p.preferredTags = d->tags;
		}
	}
	for (auto& e : effects) {
		if (e.done || e.side != side || e.windupLeft > 0 || e.def->effect != EffectKind::AttackBuff) continue;
		if (e.def->params.count("approach")) {
			p.active = true;
			p.approachDistance = std::min(p.approachDistance, e.def->param("approach"));
			p.stopDistance = std::min(p.stopDistance, e.def->param("stop", p.stopDistance));
		}
	}
	return p;
}

float Match::attackFactor(int side) const {
	float f = 1;
	for (auto& e : effects) {
		if (e.done || e.side != side || e.windupLeft > 0) continue;
		if (e.def->effect == EffectKind::AttackBuff || e.def->effect == EffectKind::ComebackBuff) f *= e.def->param("attack", 1);
	}
	return std::min(f, 1.5f);
}

float Match::defenseFactor(int side, bool consumeHit) {
	for (auto& e : effects) {
		if (e.done || e.side != side || e.windupLeft > 0 || e.def->effect != EffectKind::ComebackBuff || e.hitsLeft <= 0) continue;
		const float f = 1 - e.def->param("reduce", 0);
		if (consumeHit) {
			e.hitsLeft--;
			logf("side %d: %s absorbs a hit (%d left)", side, e.def->id.c_str(), e.hitsLeft);
		}
		return f;
	}
	return 1;
}

int Match::awakeningTicksLeft(int side) const {
	for (auto& e : effects) if (!e.done && e.side == side && e.def->family == Family::Awakenings) return e.windupLeft > 0 ? 0 : e.ticksLeft;
	return 0;
}

std::string Match::awakeningName(int side) const {
	for (auto& e : effects) if (!e.done && e.side == side && e.def->family == Family::Awakenings) return e.def->shortName;
	return "";
}

} // namespace legends
