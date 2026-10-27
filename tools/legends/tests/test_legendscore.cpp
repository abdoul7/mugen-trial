// test_legendscore.cpp -- unit tests for the Legends rules (tools/legends/engine/legendscore.cpp).
//
//   bash tools/legends/tests/run.sh        (g++ in WSL or any C++17 compiler)
//
// Uses the real generated catalog (build/game/assets/data/legends/catalog.txt, written by
// tools/legends/make_legends.py) plus small synthetic catalogs for edge cases.
#include "../engine/legendscore.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>

using namespace legends;

static int gFailed = 0, gPassed = 0;
#define CHECK(c) do { if (c) gPassed++; else { gFailed++; printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); } } while (0)

static std::string readFile(const char* p) {
	std::ifstream f(p);
	std::stringstream s;
	s << f.rdbuf();
	return s.str();
}

static Catalog gCat;

static CombatSnapshot snap(int tick = 0) {
	CombatSnapshot s;
	s.tick = tick;
	s.f[0].x = -60;
	s.f[1].x = 60;
	s.f[1].facingRight = false;
	return s;
}

static void squads(Match& m) {
	for (int s = 0; s < 2; s++)
		for (int i = 0; i < 3; i++) {
			m.squad[s].members[i].name = "F" + std::to_string(s) + std::to_string(i);
			m.squad[s].members[i].path = "chars/x" + std::to_string(i) + ".def";
		}
}

static int slotOf(Match& m, int side, const std::string& id) {
	for (int i = 0; i < 3; i++) if (!m.coach[side].hand[i].empty() && m.coach[side].hand[i].def->id == id) return i;
	return -1;
}

static void give(Match& m, int side, int slot, const std::string& id) {
	m.coach[side].hand[slot].def = gCat.find(id);
	m.coach[side].hand[slot].uid = 1000 + slot;
	m.coach[side].hand[slot].state = CardState::Ready;
}

static std::vector<Action> run(Match& m, CombatSnapshot& s, int ticks) {
	std::vector<Action> all;
	for (int i = 0; i < ticks; i++) {
		auto a = m.tick(s);
		for (auto& x : a) {
			if (x.kind == ActionKind::Damage) s.f[x.side].life = std::max(0, s.f[x.side].life - x.amount);
			if (x.kind == ActionKind::Heal) s.f[x.side].life = std::min(s.f[x.side].lifeMax, s.f[x.side].life + x.amount);
		}
		all.insert(all.end(), a.begin(), a.end());
		s.tick++;
	}
	return all;
}

static void testCatalog() {
	printf("catalog\n");
	CHECK(gCat.cards.size() == 12);
	int enabled = 0;
	for (auto& c : gCat.cards) enabled += c.enabled;
	CHECK(enabled == 7);
	CHECK(gCat.find("za_warudo") && !gCat.find("za_warudo")->enabled && !gCat.find("za_warudo")->disabledReason.empty());
	Catalog bad;
	CHECK(!parseCatalog("[card a]\nfamily = nonsense\nrarity = common\nname = A\nshort = A\neffect = heal\nenabled = 1\n", &bad).empty());
	CHECK(!parseCatalog("[card a]\nfamily = resolve\nrarity = common\nname = A\nshort = A\neffect = coach_profile\nenabled = 1\n"
		"[card a]\nfamily = resolve\nrarity = common\nname = A\nshort = A\neffect = coach_profile\nenabled = 1\n", &bad).empty()); // duplicate id
	CHECK(!parseCatalog("[card a]\nfamily = resolve\nrarity = common\nname = A\nshort = A\neffect = none\nenabled = 1\n", &bad).empty()); // enabled, no effect
	CHECK(!parseCatalog("[card a]\nfamily = resolve\nrarity = rare\nname = A\nshort = A\neffect = coach_profile\nenabled = 1\n", &bad).empty()); // no enabled common
}

static void testOpeningAndSeeds() {
	printf("opening deal, seeds\n");
	int guaranteed = 0, okRarity = 0, unique = 0;
	for (uint64_t seed = 1; seed <= 500; seed++) {
		Match m(&gCat, seed);
		squads(m);
		m.dealOpening(0);
		auto& h = m.coach[0].hand;
		guaranteed += (!h[0].empty() && h[0].def->family == Family::Resolve);
		bool cr = true;
		for (int i = 1; i < 3; i++) cr = cr && !h[i].empty() && (h[i].def->rarity == Rarity::Common || h[i].def->rarity == Rarity::Rare);
		okRarity += cr;
		unique += (h[0].def != h[1].def && h[1].def != h[2].def && h[0].def != h[2].def);
	}
	CHECK(guaranteed == 500);
	CHECK(okRarity == 500);
	CHECK(unique == 500);
	Match a(&gCat, 42), b(&gCat, 42), c(&gCat, 43);
	squads(a); squads(b); squads(c);
	a.dealOpening(0); b.dealOpening(0); c.dealOpening(0);
	bool same = true;
	for (int i = 0; i < 3; i++) same = same && a.coach[0].hand[i].def == b.coach[0].hand[i].def;
	CHECK(same);                         // reproducible from the seed
	CHECK(a.coach[0].rng.s != c.coach[0].rng.s);
}

static void testRarityOdds() {
	printf("rarity odds (empty Legendary bucket renormalised)\n");
	Match m(&gCat, 7);
	squads(m);
	std::array<int, 4> n{{0, 0, 0, 0}};
	const int N = 30000;
	for (int i = 0; i < N; i++) {
		const auto* d = m.drawCard(0, false, nullptr, "test");
		n[int(d->rarity)]++;
		m.coach[0].hand = {};             // keep every bucket eligible
		m.coach[0].uses.clear();
	}
	m.log.clear();
	// enabled: Common 4 cards, Rare 2, Epic 1, Legendary 0 -> 55/97, 30/97, 12/97
	CHECK(std::fabs(n[0] / double(N) - 55 / 97.0) < 0.015);
	CHECK(std::fabs(n[1] / double(N) - 30 / 97.0) < 0.015);
	CHECK(std::fabs(n[2] / double(N) - 12 / 97.0) < 0.015);
	CHECK(n[3] == 0);
}

static void testLegendaryCap() {
	printf("one Legendary per coach per encounter\n");
	Catalog c;
	std::string err = parseCatalog(
		"[card a]\nfamily = plot_twists\nrarity = common\nname = A\nshort = A\neffect = heal\nenabled = 1\n"
		"[card l]\nfamily = plot_twists\nrarity = legendary\nname = L\nshort = L\neffect = heal\nenabled = 1\n"
		"[legends]\nrarity.weights = 1,0,0,100000\n", &c);
	CHECK(err.empty());
	if (!err.empty()) { printf("%s", err.c_str()); return; }
	Match m(&c, 3);
	squads(m);
	const auto* first = m.drawCard(0, false, nullptr, "t");
	if (!first) { for (auto& l : m.log) printf("  log: %s\n", l.c_str()); for (auto& d : c.cards) printf("  card %s enabled %d rarity %d weight %d\n", d.id.c_str(), d.enabled, int(d.rarity), c.rarityWeights[int(d.rarity)]); }
	CHECK(first && first->id == "l");
	if (!first) return;
	m.coach[0].hand = {};              // discarded: still no second Legendary
	CHECK(m.drawCard(0, false, nullptr, "t")->id == "a");
	CHECK(m.drawCard(1, false, nullptr, "t")->id == "l"); // the other coach has its own cap
}

static void testHype() {
	printf("hype, tickets, full hand\n");
	Match m(&gCat, 5);
	squads(m);
	auto s = snap();
	m.coach[0].hand = {};
	run(m, s, 899);
	CHECK(m.coach[0].handCount() == 0);
	run(m, s, 1);
	CHECK(m.coach[0].handCount() == 1);    // a draw every 900 combat ticks
	CHECK(m.coach[0].hype == 0);
	// full hand: the ticket waits, Hype stays capped, no second ticket
	m.dealOpening(0);
	while (m.coach[0].handCount() < 3) m.drawCard(0, false, nullptr, "fill");
	run(m, s, 1800);
	CHECK(m.coach[0].tickets.size() == 1);
	CHECK(m.coach[0].hype == gCat.hypeMax);
	m.coach[0].hand[1] = CardInstance();   // a slot opens: the waiting ticket is delivered
	run(m, s, 1);
	CHECK(m.coach[0].handCount() == 3);
	CHECK(m.coach[0].tickets.empty());
	// paused combat gives nothing
	const int h = m.coach[0].hype;
	s.combatActive = false;
	run(m, s, 300);
	CHECK(m.coach[0].hype == h);
	s.combatActive = true;
	// bonus events: +60 each, at most +120 per rolling 60 ticks
	Match e(&gCat, 6);
	squads(e);
	for (int i = 0; i < 5; i++) e.addHypeEvent(0, 100);
	CHECK(e.coach[0].hype == 120);
	e.addHypeEvent(0, 161);
	CHECK(e.coach[0].hype == 180);
}

static void testPotOfGreed() {
	printf("Pot of Greed: bounded ticket queue, once per encounter\n");
	Match m(&gCat, 9);
	squads(m);
	auto s = snap();
	give(m, 0, 0, "pot_of_greed");
	give(m, 0, 1, "senzu_bean");
	give(m, 0, 2, "chidori");
	m.coach[0].tickets = {'N'};
	CHECK(m.requestPlay(0, 0, s).empty());
	run(m, s, 1);
	CHECK(m.coach[0].handCount() == 3);     // the freed slot was refilled at once
	int b = 0;
	for (char t : m.coach[0].tickets) b += t == 'B';
	CHECK(m.coach[0].tickets.size() <= 3 && b <= 2);
	m.coach[0].cooldown = 0;
	give(m, 0, 2, "pot_of_greed");
	CHECK(m.requestPlay(0, 2, s) == "USED");
}

static void testActivation() {
	printf("activation: rejected / armed / committed, cooldown, expiry, one reservation\n");
	Match m(&gCat, 11);
	squads(m);
	auto s = snap();
	give(m, 0, 0, "senzu_bean");
	give(m, 0, 1, "spirit_gun");
	give(m, 0, 2, "chidori");
	s.f[0].life = 500;
	s.f[0].grounded = false;              // not a legal opening for Senzu (needs ground)
	CHECK(m.requestPlay(0, 0, s).empty());
	CHECK(m.coach[0].hand[0].state == CardState::Armed);
	CHECK(m.requestPlay(0, 1, s) == "ONE AT A TIME");
	run(m, s, 61);                        // 60-tick reservation runs out
	CHECK(m.coach[0].hand[0].state == CardState::Ready);
	CHECK(m.coach[0].cooldown == 0 && m.coach[0].uses["senzu_bean"] == 0); // no cost
	s.f[0].grounded = true;
	CHECK(m.requestPlay(0, 0, s).empty());
	run(m, s, 1);
	CHECK(slotOf(m, 0, "senzu_bean") < 0); // consumed at commitment
	CHECK(m.coach[0].cooldown == gCat.playCooldown - 1);
	CHECK(m.requestPlay(0, 1, s) == "COOLDOWN");
	const int life = s.f[0].life;
	run(m, s, 30);                        // 30-tick windup, then the heal
	CHECK(s.f[0].life == life + 120);
	// a heal at full HP is kept in hand
	Match f(&gCat, 12);
	squads(f);
	auto s2 = snap();
	give(f, 0, 0, "senzu_bean");
	CHECK(f.requestPlay(0, 0, s2) == "FULL HP");
}

static void testInterruption() {
	printf("windup interrupted by a hit: card lost, no heal\n");
	Match m(&gCat, 13);
	squads(m);
	auto s = snap();
	s.f[0].life = 400;
	give(m, 0, 0, "senzu_bean");
	m.requestPlay(0, 0, s);
	run(m, s, 5);
	s.f[0].gotHit = true;
	run(m, s, 1);
	s.f[0].gotHit = false;
	run(m, s, 40);
	CHECK(s.f[0].life == 400);
	CHECK(slotOf(m, 0, "senzu_bean") < 0);
	CHECK(m.effects.empty());
}

static void testAwakenings() {
	printf("awakenings: duration from activation, strain never KOs, one at a time, cleanup\n");
	Match m(&gCat, 14);
	squads(m);
	auto s = snap();
	give(m, 0, 0, "kaio_ken");
	give(m, 0, 1, "plus_ultra");
	CHECK(m.requestPlay(0, 0, s).empty());
	run(m, s, 1);
	CHECK(m.attackFactor(0) == 1.0f);       // 6-tick windup: nothing yet
	CHECK(m.awakeningTicksLeft(0) == 0);
	run(m, s, 6);
	CHECK(std::fabs(m.attackFactor(0) - 1.2f) < 1e-4);
	CHECK(m.awakeningTicksLeft(0) == 358);  // the 360-tick duration counts from activation
	m.coach[0].cooldown = 0;
	s.f[0].life = 300;                    // below 35% for PLUS ULTRA, but Kaio-ken is active
	CHECK(m.requestPlay(0, 1, s) == "AWAKENING ACTIVE");
	s.f[0].life = 3;
	run(m, s, 300);
	CHECK(s.f[0].life == 1);              // strain stops at 1 HP
	CHECK(m.profileFor(0).active && m.profileFor(0).approachDistance <= 26);
	m.endBout(judgeBout(s.f[0], s.f[1], true));
	CHECK(m.effects.empty());
	CHECK(m.attackFactor(0) == 1.0f);
	// PLUS ULTRA: below 35% only; reduces the next two hits
	Match p(&gCat, 15);
	squads(p);
	auto t = snap();
	give(p, 0, 0, "plus_ultra");
	CHECK(p.requestPlay(0, 0, t).empty());   // armed: waits for HP below 35%
	run(p, t, 1);
	CHECK(p.coach[0].hand[0].state == CardState::Armed && p.coach[0].hand[0].reason == "WAIT: HP");
	t.f[0].life = 300;
	run(p, t, 7);
	CHECK(std::fabs(p.defenseFactor(0, true) - 0.65f) < 1e-4);
	CHECK(std::fabs(p.defenseFactor(0, true) - 0.65f) < 1e-4);
	CHECK(p.defenseFactor(0, true) == 1.0f);
	// once per fighter: the same fighter cannot use it again, the next squad member can
	p.endBout(judgeBout(t.f[0], t.f[1], true));
	p.squad[0].active = 0;
	p.coach[0].cooldown = 0;
	give(p, 0, 1, "plus_ultra");
	CHECK(p.requestPlay(0, 1, t) == "USED BY THIS FIGHTER");
	p.squad[0].active = 1;
	CHECK(p.requestPlay(0, 1, t).empty());
}

static void testEcho() {
	printf("echo projectile: hit, block, miss\n");
	for (int mode = 0; mode < 3; mode++) {
		Match m(&gCat, 16);
		squads(m);
		auto s = snap();
		if (mode == 2) s.f[1].x = 400;     // out of range
		s.f[1].guarding = mode == 1;
		give(m, 0, 0, "spirit_gun");
		m.requestPlay(0, 0, s);
		auto a = run(m, s, 120);
		int dmg = 0, ends = 0, spawns = 0;
		for (auto& x : a) {
			dmg += x.kind == ActionKind::Damage && x.side == 1 ? x.amount : 0;
			ends += x.kind == ActionKind::EchoEnd;
			spawns += x.kind == ActionKind::EchoSpawn;
		}
		CHECK(spawns == 1 && ends == 1);
		if (mode == 0) CHECK(dmg == 50);     // 5% of 1000
		else CHECK(dmg == 0);
	}
}

static void testSimultaneous() {
	printf("simultaneous plays alternate\n");
	Match m(&gCat, 17);
	squads(m);
	auto s = snap();
	std::vector<int> firsts;
	for (int round = 0; round < 4; round++) {
		give(m, 0, 0, "kaio_ken");
		give(m, 1, 0, "kaio_ken");
		m.coach[0].cooldown = m.coach[1].cooldown = 0;
		m.effects.clear();
		m.log.clear();
		m.requestPlay(0, 0, s);
		m.requestPlay(1, 0, s);
		run(m, s, 1);
		for (auto& l : m.log) if (l.find("simultaneous") != std::string::npos) firsts.push_back(l[l.find("side ") + 5] - '0');
	}
	CHECK(firsts.size() == 4);
	if (firsts.size() == 4) CHECK(firsts[0] != firsts[1] && firsts[1] != firsts[2] && firsts[2] != firsts[3]);
}

static void testKO() {
	printf("a KO'd fighter cannot play\n");
	Match m(&gCat, 18);
	squads(m);
	auto s = snap();
	s.f[0].alive = false;
	give(m, 0, 0, "kaio_ken");
	CHECK(m.requestPlay(0, 0, s) == "KO");
}

static void testRelay() {
	printf("relay: judging, HP carryover, eliminations, draw\n");
	FighterView a, b;
	a.life = 400; b.life = 600;
	auto r = judgeBout(a, b, true);
	CHECK(r.lost[0] && !r.lost[1]);
	b.lifeMax = 1500; b.life = 600;      // fractions, not raw HP: 0.4 vs 0.4 -> both out
	r = judgeBout(a, b, true);
	CHECK(r.lost[0] && r.lost[1]);
	a.alive = b.alive = false;
	r = judgeBout(a, b, false);
	CHECK(r.how == BoutEnd::KO && r.lost[0] && r.lost[1]);

	Match m(&gCat, 19);
	squads(m);
	m.startBout();
	FighterView w, l;
	w.life = 700; l.alive = false; l.life = 0;
	m.endBout(judgeBout(w, l, false));
	CHECK(m.squad[0].active == 0 && std::fabs(m.squad[0].members[0].hpFraction - 0.7f) < 1e-4);
	CHECK(m.squad[1].active == 1 && m.squad[1].members[1].hpFraction == 1.0f);
	CHECK(!m.over());
	m.startBout(); m.endBout(judgeBout(w, l, false));
	m.startBout(); m.endBout(judgeBout(w, l, false));
	CHECK(m.over() && m.winner() == 0);

	Match d(&gCat, 20);
	squads(d);
	FighterView x, y;
	x.alive = y.alive = false;
	for (int i = 0; i < 3; i++) { d.startBout(); d.endBout(judgeBout(x, y, false)); }
	CHECK(d.over() && d.winner() == -1);
}

static void testResolve() {
	printf("resolve: opening attach, replacement, profile\n");
	Match m(&gCat, 21);
	squads(m);
	m.dealOpening(0);
	CHECK(m.attachResolve(0, 0, 2));
	CHECK(m.squad[0].members[2].resolveId == "my_ninja_way");
	CHECK(m.coach[0].hand[0].empty());
	CHECK(!m.profileFor(0).active);       // attached to the third fighter, not the first
	m.squad[0].active = 2;
	const auto p = m.profileFor(0);
	CHECK(p.active && p.approachDistance == 24 && p.tagBias == 0); // no adapter: no tagged moves
	m.squad[0].members[2].hasAdapter = true;
	CHECK(m.profileFor(0).tagBias > 0);
	auto s = snap();
	give(m, 0, 1, "my_ninja_way");
	CHECK(m.requestPlay(0, 1, s) == "EQUIPPED");
}

static void testCpuCoach() {
	printf("CPU coach: same rules, plays over time\n");
	Match m(&gCat, 22);
	squads(m);
	m.setCpu(1, true);
	m.dealOpening(1);
	m.cpuChooseOpening(1);
	CHECK(!m.squad[1].members[0].resolveId.empty());
	auto s = snap();
	s.f[1].life = 400;
	run(m, s, 1800);
	CHECK(m.coach[1].cardsPlayed >= 2);
	int plays = 0;
	for (auto& l : m.log) plays += l.find("side 1 commits") != std::string::npos;
	CHECK(plays + 1 == m.coach[1].cardsPlayed); // +1: the opening Resolve
	CHECK(m.coach[1].cooldown <= gCat.playCooldown);
}

static void testDrawBan() {
	printf("per-coach draw ban: opening and repeated ticket draws\n");
	Match m(&gCat, 1234);
	squads(m);
	m.coach[0].bannedCards = {"my_ninja_way"};
	m.dealOpening(0);
	CHECK(!m.coach[0].holds("my_ninja_way"));
	for (int i = 0; i < 200; ++i) {
		for (auto& h : m.coach[0].hand) h = CardInstance();
		const auto* d = m.drawCard(0, false, nullptr, "ban regression");
		CHECK(d && d->id != "my_ninja_way");
	}
	Family resolve = Family::Resolve;
	CHECK(m.eligible(0, false, &resolve).empty());
	CHECK(!m.eligible(1, false, &resolve).empty()); // opponent is unaffected
}

static void testAdapters() {
	printf("adapters\n");
	std::vector<Adapter> a;
	CHECK(parseAdapters(readFile("build/game/assets/data/legends/adapters.txt"), &a).empty());
	CHECK(a.size() == 2);
	CHECK(findAdapter(a, "assets/chars/kfm/kfm.def") && findAdapter(a, "assets/chars/kfm/kfm.def")->tags.at("approach")[0] == "FF");
	CHECK(findAdapter(a, "assets/chars/Pupa/Pupa.def") != nullptr);
	CHECK(findAdapter(a, "assets/chars/goenitz/goenitz.def") == nullptr);
}

int main() {
	setvbuf(stdout, nullptr, _IONBF, 0);
	const auto err = parseCatalog(readFile("build/game/assets/data/legends/catalog.txt"), &gCat);
	if (!err.empty()) {
		printf("catalog does not parse:\n%s", err.c_str());
		return 1;
	}
	testCatalog();
	testOpeningAndSeeds();
	testRarityOdds();
	testLegendaryCap();
	testHype();
	testPotOfGreed();
	testActivation();
	testInterruption();
	testAwakenings();
	testEcho();
	testSimultaneous();
	testKO();
	testRelay();
	testResolve();
	testCpuCoach();
	testAdapters();
	testDrawBan();
	printf("%d passed, %d failed\n", gPassed, gFailed);
	return gFailed ? 1 : 0;
}
