// legendsmode.cpp -- see legendsmode.h. Section numbers refer to docs/legends-design.md.
#include "legendsmode.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <memory>

#include <prism/file.h>
#include <prism/input.h>
#include <prism/log.h>
#include <prism/mugenanimationhandler.h>
#include <prism/mugenanimationreader.h>
#include <prism/mugendefreader.h>
#include <prism/mugenspritefilereader.h>
#include <prism/mugentexthandler.h>
#include <prism/screeneffect.h>
#include <prism/wrapper.h>

#include "characterselectscreen.h"
#include "config.h"
#include "fightscreen.h"
#include "gamelogic.h"
#include "legendscore.h"
#include "mugenstatereader.h"
#include "playerdefinition.h"
#include "stage.h"
#include "titlescreen.h"
#include "versusscreen.h"

#ifdef VITA
#include <psp2/kernel/processmgr.h>
#define LEGENDS_DATA_DIR "ux0:data/JFVT00001/"
#else
#define LEGENDS_DATA_DIR ""
#endif

using namespace prism;

// Fonts of the jfv motif (tools/make_ui.py), all drawn at 2x: texts here are scaled by 0.5
static const int SYS_FONT_SMALL = 1, SYS_FONT_HEAD = 8, SYS_FONT_MED = 10, SYS_FONT_LIST = 11, SYS_FONT_RULES = 12;
static const int FIGHT_FONT_MED = 1, FIGHT_FONT_SMALL = 3, FIGHT_FONT_XS = 9, FIGHT_FONT_RULES = 10;
static const float TEXT_SCALE = 0.5f, ART_SCALE = 0.5f;

// legends.sff sprite groups (tools/legends/legends_art.py)
enum {
	SPR_BACKDROP = 1, SPR_PANEL = 2, SPR_CARD_FACE = 3, SPR_TILE = 10, SPR_FOCUS = 11, SPR_ARMED = 12, SPR_EMPTY = 13,
	SPR_ICON = 20, SPR_PIPS = 21, SPR_HYPE = 30, SPR_TICKET = 31, SPR_ECHO = 40, SPR_SPARK = 41, SPR_SQUAD = 50,
	SPR_BANNER = 60, SPR_INSPECT = 61, SPR_CARD_BACK = 62, SPR_ROW = 63,
};

struct ColorF { float r, g, b; };
static const ColorF FAMILY_COLOR[4] = {{0.35f, 0.9f, 0.85f}, {1.0f, 0.6f, 0.2f}, {1.0f, 0.35f, 0.35f}, {0.75f, 0.55f, 1.0f}};
static const ColorF SIDE_COLOR[2] = {{0.45f, 0.8f, 1.0f}, {1.0f, 0.45f, 0.5f}};

enum class LegendsScreenMode { Setup, Relay, Results, Error };

static struct {
	legends::Catalog mCatalog;
	std::vector<legends::Adapter> mAdapters;
	std::unique_ptr<legends::Match> mMatch;
	std::string mError;
	uint64_t mSeed = 1;
	int mPickIndex = 0;
	std::vector<std::string> mPicks; // player squad .def paths, in pick order (= squad order)
	LegendsScreenMode mScreenMode = LegendsScreenMode::Setup;
	std::string mLastBoutText;
	int mIsBoutActive = 0;
	int mIsAutotest = 0;
	int mIsAutotestPending = 0;
	int mAutotestAttach = 1;
	int mAutotestInspect = 0, mAutotestSetupTicks = 60;
	std::vector<std::string> mAutotestBan;
	size_t mLogFlushed = 0;
} gLegends;

// Kit sprite IDs are generated from the catalog order, never from the family.
static int cardArtIndex(const legends::CardDef* d) {
	for (size_t i = 0; i < gLegends.mCatalog.cards.size(); ++i)
		if (&gLegends.mCatalog.cards[i] == d) return int(i);
	return -1;
}

// ------------------------------------------------------------------ helpers
static std::string readTextFile(const std::string& tPath) {
	if (!isFile(tPath)) return "";
	Buffer b = fileToBuffer(tPath.c_str());
	std::string s((const char*)b.mData, b.mLength);
	freeBuffer(b);
	return s;
}

static void flushLegendsLog() {
	if (!gLegends.mMatch) return;
	auto& log = gLegends.mMatch->log;
	FILE* f = fopen(LEGENDS_DATA_DIR "legends_log.txt", "a");
	for (; gLegends.mLogFlushed < log.size(); gLegends.mLogFlushed++) {
		logFormat("[LEGENDS] %s", log[gLegends.mLogFlushed].c_str());
		if (f) fprintf(f, "%s\n", log[gLegends.mLogFlushed].c_str());
	}
	if (f) fclose(f);
}

static std::string characterDisplayName(const std::string& tDefPath) {
	MugenDefScript script;
	loadMugenDefScript(&script, tDefPath);
	auto name = getSTLMugenDefStringOrDefault(&script, "info", "displayname", "");
	if (name.empty()) name = getSTLMugenDefStringOrDefault(&script, "info", "name", "?");
	unloadMugenDefScript(&script);
	for (auto& c : name) c = char(toupper(c));
	return name;
}

static void fillMember(legends::SquadMember* m, const std::string& tPath) {
	m->path = tPath;
	m->name = characterDisplayName(tPath);
	m->hpFraction = 1;
	m->eliminated = false;
	m->resolveId.clear();
	m->hasAdapter = legends::findAdapter(gLegends.mAdapters, tPath) != nullptr;
}

static int loadLegendsData() {
	const auto folder = getDolmexicaAssetFolder() + "data/legends/";
	const auto catalogText = readTextFile(folder + "catalog.txt");
	if (catalogText.empty()) {
		gLegends.mError = "data/legends/catalog.txt is missing (run tools/legends/make_legends.py)";
		return 0;
	}
	gLegends.mError = legends::parseCatalog(catalogText, &gLegends.mCatalog);
	if (!gLegends.mError.empty()) return 0;
	gLegends.mError = legends::parseAdapters(readTextFile(folder + "adapters.txt"), &gLegends.mAdapters);
	return gLegends.mError.empty();
}

// every character in select.def, for the CPU squad
static void addRosterEntry(void* tCaller, void* tData) {
	auto* out = (std::vector<std::string>*)tCaller;
	auto* element = (MugenDefScriptGroupElement*)tData;
	const char* name = nullptr;
	if (element->mType == MUGEN_DEF_SCRIPT_GROUP_VECTOR_ELEMENT) name = ((MugenDefScriptVectorElement*)element->mData)->mVector.mElement[0];
	else if (element->mType == MUGEN_DEF_SCRIPT_GROUP_STRING_ELEMENT) name = ((MugenDefScriptStringElement*)element->mData)->mString;
	if (!name || !strcmp(name, "randomselect")) return;
	char path[1024];
	getCharacterSelectNamePath(name, path);
	if (isFile(path)) out->push_back(path);
}

static std::vector<std::string> loadRoster() {
	std::vector<std::string> roster;
	MugenDefScript script;
	loadMugenDefScript(&script, getDolmexicaAssetFolder() + "data/select.def");
	list_map(&script.mGroups["characters"].mOrderedElementList, addRosterEntry, &roster);
	unloadMugenDefScript(&script);
	return roster;
}

static void chooseCpuSquad() {
	auto roster = loadRoster();
	legends::Rng rng(gLegends.mSeed ^ 0xC0FFEEull);
	for (int i = 0; i < 3 && !roster.empty(); i++) {
		const int k = rng.range(0, int(roster.size()) - 1);
		fillMember(&gLegends.mMatch->squad[1].members[i], roster[k]);
		roster.erase(roster.begin() + k); // three distinct fighters
	}
}

static void newMatch() {
	gLegends.mSeed = gLegends.mIsAutotest ? gLegends.mSeed : uint64_t(time(nullptr)) ^ (getSystemTicks() << 7);
	gLegends.mMatch.reset(new legends::Match(&gLegends.mCatalog, gLegends.mSeed));
	gLegends.mLogFlushed = 0;
	gLegends.mMatch->boutTickLimit = 90 * 60;
	gLegends.mMatch->setCpu(1, true);
	gLegends.mMatch->setCpu(0, gLegends.mIsAutotest != 0);
}

// ------------------------------------------------------------------ relay flow
static void startNextBout();
static void showLegendsScreen(LegendsScreenMode tMode);

static void boutFinished();

static void versusFinished() {
	auto& m = *gLegends.mMatch;
	setGameModeLegends();
	// winner keeps its HP fraction, an incoming fighter starts full (section 3)
	setPlayerStartLifePercentage(0, m.squad[0].members[m.squad[0].active].hpFraction);
	setPlayerStartLifePercentage(1, m.squad[1].members[m.squad[1].active].hpFraction);
	gLegends.mIsBoutActive = 1;
	startFightScreen(boutFinished, boutFinished);
}

static void startNextBout() {
	auto& m = *gLegends.mMatch;
	m.startBout();
	flushLegendsLog();
	setPlayerDefinitionPath(0, m.squad[0].members[m.squad[0].active].path.c_str());
	setPlayerDefinitionPath(1, m.squad[1].members[m.squad[1].active].path.c_str());
	MugenDefScript script;
	loadMugenDefScript(&script, getDolmexicaAssetFolder() + "data/select.def");
	setStageRandom(&script);
	unloadMugenDefScript(&script);
	if (gLegends.mIsAutotest) {
		versusFinished();
		return;
	}
	setVersusScreenNoMatchNumber();
	setVersusScreenFinishedCB(versusFinished);
	setNewScreen(getVersusScreen());
}

static legends::BoutResult gPendingResult;
static int gHasPendingResult = 0;
static void logBoutTelemetry();

static void boutFinished() {
	if (!gLegends.mIsBoutActive) return; // the engine and Legends may both end a bout: once only
	gLegends.mIsBoutActive = 0;
	auto& m = *gLegends.mMatch;
	logBoutTelemetry();
	legends::BoutResult r = gPendingResult;
	if (!gHasPendingResult) { // the engine ended the fight before Legends decided: judge it from the fighters now
		legends::FighterView f[2];
		for (int i = 0; i < 2; i++) {
			f[i].alive = isPlayerAlive(getRootPlayer(i)) != 0;
			f[i].life = getPlayerLife(getRootPlayer(i));
			f[i].lifeMax = getPlayerLifeMax(getRootPlayer(i));
		}
		r = legends::judgeBout(f[0], f[1], true);
	}
	gHasPendingResult = 0;
	const auto a = m.squad[0].members[m.squad[0].active].name, b = m.squad[1].members[m.squad[1].active].name;
	if (r.lost[0] && r.lost[1]) gLegends.mLastBoutText = a + " AND " + b + " ARE OUT";
	else if (r.lost[0]) gLegends.mLastBoutText = a + " IS OUT";
	else if (r.lost[1]) gLegends.mLastBoutText = b + " IS OUT";
	else gLegends.mLastBoutText = "NO RESULT";
	if (r.how == legends::BoutEnd::Timeout) gLegends.mLastBoutText += " (TIME)";
	m.endBout(r);
	flushLegendsLog();
	showLegendsScreen(m.over() ? LegendsScreenMode::Results : LegendsScreenMode::Relay);
}

// ------------------------------------------------------------------ squad select
static void squadPickFinished();

static void openSquadSelect(const char* tTitle) {
	setCharacterSelectScreenModeName(tTitle);
	setCharacterSelectOnePlayer();
	setCharacterSelectStageInactive();
	setCharacterSelectFinishedCB(squadPickFinished);
	setNewScreen(getCharacterSelectScreen());
}

static void squadPickFinished() {
	char path[1024];
	getPlayerDefinitionPath(path, 0);
	for (auto& p : gLegends.mPicks) {
		if (p == path) {
			openSquadSelect("LEGENDS: PICK ANOTHER FIGHTER");
			return;
		}
	}
	gLegends.mPicks.push_back(path);
	if (gLegends.mPicks.size() < 3) {
		openSquadSelect(gLegends.mPicks.size() == 1 ? "LEGENDS: FIGHTER 2 OF 3" : "LEGENDS: FIGHTER 3 OF 3");
		return;
	}
	newMatch();
	for (int i = 0; i < 3; i++) fillMember(&gLegends.mMatch->squad[0].members[i], gLegends.mPicks[i]);
	chooseCpuSquad();
	gLegends.mMatch->dealOpening(0);
	gLegends.mMatch->dealOpening(1);
	gLegends.mMatch->cpuChooseOpening(1);
	showLegendsScreen(LegendsScreenMode::Setup);
}

void startLegendsMode() {
	gLegends.mIsAutotest = 0;
	gLegends.mPicks.clear();
	if (!loadLegendsData()) {
		logWarningFormat("[LEGENDS] %s", gLegends.mError.c_str());
		showLegendsScreen(LegendsScreenMode::Error);
		return;
	}
	openSquadSelect("LEGENDS: FIGHTER 1 OF 3");
}

// ------------------------------------------------------------------ the Legends screen (setup, relay, results)
static struct {
	MugenSpriteFile mSprites;
	std::vector<MugenAnimation*> mAnimations;
	std::vector<int> mTexts;
	int mFocus = 0;          // setup: squad member the Resolve goes to
	int mResolveSlot = -1;
	int mNow = 0;
	int mHintID = -1, mTargetID = -1;
	std::array<int, 3> mMemberIDs{{-1, -1, -1}};
} gScreen;

static MugenAnimationHandlerElement* addSprite(MugenSpriteFile* tSprites, std::vector<MugenAnimation*>* tOwned, int g, int i, float x, float y, float z) {
	if (!hasMugenSprite(tSprites, g, i)) return nullptr;
	MugenAnimation* a = createOneFrameMugenAnimationForSprite(g, i);
	tOwned->push_back(a);
	auto* e = addMugenAnimation(a, tSprites, Vector3D(x, y, z));
	setMugenAnimationBaseDrawScale(e, ART_SCALE);
	return e;
}

static int addText(const std::string& tText, float x, float y, int tFont, MugenTextAlignment tAlign, ColorF c, float z = 80) {
	const int id = addMugenText(tText.c_str(), Vector3D(x, y, z), tFont);
	setMugenTextScale(id, TEXT_SCALE);
	setMugenTextAlignment(id, tAlign);
	setMugenTextColorRGB(id, c.r, c.g, c.b);
	return id;
}

static const ColorF WHITE = {1, 1, 1}, GREY = {0.7f, 0.75f, 0.85f}, ORANGE = {1, 0.62f, 0.2f}, GREEN = {0.5f, 1, 0.6f};

static std::string squadLine(const legends::SquadMember& m) {
	char b[160];
	if (m.eliminated) snprintf(b, sizeof(b), "%s OUT", m.name.c_str());
	else snprintf(b, sizeof(b), "%s %d%%%s%s", m.name.c_str(), int(std::lround(m.hpFraction * 100)), m.resolveId.empty() ? "" : " +",
		m.resolveId.empty() ? "" : gLegends.mCatalog.find(m.resolveId)->shortName.c_str());
	return b;
}

static void drawSquads(float y, int tMarkFocus) {
	auto& m = *gLegends.mMatch;
	addText("YOUR SQUAD", 24, y, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_LEFT, SIDE_COLOR[0]);
	addText("CPU SQUAD", 296, y, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_RIGHT, SIDE_COLOR[1]);
	for (int i = 0; i < 3; i++) {
		const bool active = i == m.squad[0].active && !m.squad[0].members[i].eliminated;
		const std::string mark = tMarkFocus ? "  " : active ? "> " : "  ";
		gScreen.mMemberIDs[i] = addText(mark + squadLine(m.squad[0].members[i]), 24, y + 10 + i * 9, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_LEFT, m.squad[0].members[i].eliminated ? GREY : WHITE);
		addText(squadLine(m.squad[1].members[i]), 296, y + 10 + i * 9, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_RIGHT, m.squad[1].members[i].eliminated ? GREY : WHITE);
	}
}

static void drawCardFace(const legends::CardDef* d, float x, float y) {
	const int f = int(d->family);
	const int index = cardArtIndex(d);
	if (hasMugenSprite(&gScreen.mSprites, 100, index)) {
		// 128x192 source pixels -> 64x96 in 320-space. Text stays native.
		addSprite(&gScreen.mSprites, &gScreen.mAnimations, 100, index, x + 6, y, 60);
		addText(d->shortName, x + 38, y + 104, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE, 63);
		return;
	}
	addSprite(&gScreen.mSprites, &gScreen.mAnimations, SPR_CARD_FACE, f, x, y, 60);
	addSprite(&gScreen.mSprites, &gScreen.mAnimations, SPR_PIPS, int(d->rarity), x + 52, y + 5, 62);
	addText(legends::familyName(d->family), x + 5, y + 11, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_LEFT, FAMILY_COLOR[f], 63);
	addText(d->shortName, x + 38, y + 61, SYS_FONT_SMALL, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE, 63);
	const int t = addText(d->text, x + 5, y + 71, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_LEFT, GREY, 63);
	setMugenTextTextBoxWidth(t, 66);
}

static void loadLegendsScreen() {
	gScreen.mSprites = loadMugenSpriteFileWithoutPalette(getDolmexicaAssetFolder() + "data/legends/legends.sff");
	gScreen.mAnimations.clear();
	gScreen.mNow = 0;
	addSprite(&gScreen.mSprites, &gScreen.mAnimations, SPR_BACKDROP, 0, 0, 0, 1);
	addSprite(&gScreen.mSprites, &gScreen.mAnimations, SPR_PANEL, 0, 12, 18, 2);
	addText("LEGENDS", 24, 33, SYS_FONT_HEAD, MUGEN_TEXT_ALIGNMENT_LEFT, WHITE);
	if (gLegends.mScreenMode == LegendsScreenMode::Error) {
		addText("LEGENDS CANNOT START", 24, 58, SYS_FONT_MED, MUGEN_TEXT_ALIGNMENT_LEFT, ORANGE);
		const int t = addText(gLegends.mError, 24, 72, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_LEFT, WHITE);
		setMugenTextTextBoxWidth(t, 270);
		addText("CIRCLE: BACK", 296, 226, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_RIGHT, GREY);
		return;
	}
	auto& m = *gLegends.mMatch;
	if (gLegends.mScreenMode == LegendsScreenMode::Setup) {
		addText("OPENING DEAL", 296, 33, SYS_FONT_MED, MUGEN_TEXT_ALIGNMENT_RIGHT, ORANGE);
		gScreen.mResolveSlot = -1;
		for (int i = 0; i < 3; i++) {
			const auto& h = m.coach[0].hand[i];
			if (h.empty()) continue;
			drawCardFace(h.def, 24 + i * 98, 42);
			if (h.def->family == legends::Family::Resolve && gScreen.mResolveSlot < 0) gScreen.mResolveSlot = i;
		}
		drawSquads(158, 1);
		gScreen.mFocus = 0;
		gScreen.mTargetID = addText(" ", 160, 206, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_CENTER, ORANGE);
		if (gScreen.mResolveSlot >= 0) {
			addText("UP/DOWN: TARGET   CROSS: ATTACH + FIGHT", 160, 217, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
			addText("CIRCLE: KEEP IN HAND", 160, 226, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
		}
		else addText("CROSS: FIGHT", 160, 226, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
	}
	else if (gLegends.mScreenMode == LegendsScreenMode::Relay) {
		addText("BOUT " + std::to_string(m.boutNumber) + " OVER", 296, 33, SYS_FONT_MED, MUGEN_TEXT_ALIGNMENT_RIGHT, ORANGE);
		addText(gLegends.mLastBoutText, 160, 64, SYS_FONT_MED, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE);
		addText("ONE FIGHTER EACH PER BOUT. WINNERS KEEP THEIR HP.", 160, 78, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
		drawSquads(98, 0);
		addText("NEXT: " + m.squad[0].members[m.squad[0].active].name + "  VS  " + m.squad[1].members[m.squad[1].active].name, 160, 158, SYS_FONT_SMALL, MUGEN_TEXT_ALIGNMENT_CENTER, ORANGE);
		addText("CROSS: NEXT BOUT", 160, 226, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
	}
	else {
		const int w = m.winner();
		addText(w == 0 ? "YOUR SQUAD WINS" : w == 1 ? "THE CPU SQUAD WINS" : "DRAW", 160, 60, SYS_FONT_HEAD, MUGEN_TEXT_ALIGNMENT_CENTER, w == 0 ? GREEN : w == 1 ? SIDE_COLOR[1] : WHITE);
		addText(gLegends.mLastBoutText, 160, 74, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
		drawSquads(92, 0);
		char b[200];
		snprintf(b, sizeof(b), "YOU: %d CARDS DRAWN, %d PLAYED      CPU: %d DRAWN, %d PLAYED", m.coach[0].cardsDrawn, m.coach[0].cardsPlayed, m.coach[1].cardsDrawn, m.coach[1].cardsPlayed);
		addText(b, 160, 148, SYS_FONT_LIST, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE);
		std::string played = "YOU PLAYED: ";
		for (size_t i = 0; i < m.coach[0].playedIds.size(); i++) played += (i ? ", " : "") + gLegends.mCatalog.find(m.coach[0].playedIds[i])->shortName;
		const int t = addText(m.coach[0].playedIds.empty() ? "YOU PLAYED NO CARDS" : played, 24, 162, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_LEFT, GREY);
		setMugenTextTextBoxWidth(t, 272);
		addText("CROSS: REMATCH     TRIANGLE: NEW SQUAD     CIRCLE: MAIN MENU", 160, 226, SYS_FONT_RULES, MUGEN_TEXT_ALIGNMENT_CENTER, GREY);
	}
	addFadeIn(10, NULL, NULL);
}

static void exitToTitle() {
	gLegends.mMatch.reset();
	setNewScreen(getDreamTitleScreen());
}

static void rematch() {
	auto picks0 = gLegends.mMatch->squad[0], picks1 = gLegends.mMatch->squad[1];
	newMatch();
	for (int s = 0; s < 2; s++)
		for (int i = 0; i < 3; i++) fillMember(&gLegends.mMatch->squad[s].members[i], (s ? picks1 : picks0).members[i].path);
	gLegends.mMatch->dealOpening(0);
	gLegends.mMatch->dealOpening(1);
	gLegends.mMatch->cpuChooseOpening(1);
	showLegendsScreen(LegendsScreenMode::Setup);
}

static void updateLegendsScreen() {
	gScreen.mNow++;
	if (gLegends.mScreenMode == LegendsScreenMode::Error) {
		if (hasPressedBFlankSingle(0) || hasPressedStartFlankSingle(0)) exitToTitle();
		return;
	}
	auto& m = *gLegends.mMatch;
	const bool autotest = gLegends.mIsAutotest && gScreen.mNow > (gLegends.mScreenMode == LegendsScreenMode::Setup ? gLegends.mAutotestSetupTicks : 60);
	if (gLegends.mScreenMode == LegendsScreenMode::Setup) {
		if (gScreen.mResolveSlot >= 0) {
			if (hasPressedUpFlankSingle(0)) gScreen.mFocus = (gScreen.mFocus + 2) % 3;
			if (hasPressedDownFlankSingle(0)) gScreen.mFocus = (gScreen.mFocus + 1) % 3;
			changeMugenText(gScreen.mTargetID, ("RESOLVE GOES TO: " + m.squad[0].members[gScreen.mFocus].name).c_str());
		}
		if (hasPressedAFlankSingle(0) || autotest) {
			if (gScreen.mResolveSlot >= 0 && (!gLegends.mIsAutotest || gLegends.mAutotestAttach)) m.attachResolve(0, gScreen.mResolveSlot, gScreen.mFocus);
			startNextBout();
		}
		else if (hasPressedBFlankSingle(0)) startNextBout(); // keep the Resolve in hand
	}
	else if (gLegends.mScreenMode == LegendsScreenMode::Relay) {
		if (hasPressedAFlankSingle(0) || autotest || gScreen.mNow > 60 * 8) startNextBout();
	}
	else {
		if (gLegends.mIsAutotest && gScreen.mNow > 120) {
			m.logf("autotest complete winner %d", m.winner());
			flushLegendsLog();
			logg("[LEGENDS] autotest done");
#ifdef VITA
			sceKernelExitProcess(0);
#endif
			exitToTitle();
			return;
		}
		if (hasPressedAFlankSingle(0)) rematch();
		else if (hasPressedYFlankSingle(0)) startLegendsMode();
		else if (hasPressedBFlankSingle(0)) exitToTitle();
	}
}

static void unloadLegendsScreen() {
	unloadMugenSpriteFile(&gScreen.mSprites);
	for (auto* a : gScreen.mAnimations) destroyMugenAnimation(a);
	gScreen.mAnimations.clear();
}

static Screen gLegendsScreen;

static void showLegendsScreen(LegendsScreenMode tMode) {
	gLegends.mScreenMode = tMode;
	gLegendsScreen = makeScreen(loadLegendsScreen, updateLegendsScreen, NULL, unloadLegendsScreen);
	setNewScreen(&gLegendsScreen);
}

// ------------------------------------------------------------------ autotest
// ux0:data/JFVT00001/legends_autotest.txt: a hands-off encounter for tests (both coaches CPU):
//     seed = 1234
//     p1 = assets/chars/kfm/kfm.def, assets/chars/pupa/Pupa.def, assets/chars/bender/ben.def
//     p2 = ...
//     attach = 1            (equip the opening Resolve; 0 = keep it in hand)
// The encounter runs to the results and the process exits; legends_log.txt has the log.
int tryStartLegendsAutotest() {
	const auto text = readTextFile(LEGENDS_DATA_DIR "legends_autotest.txt");
	if (text.empty()) return 0;
	if (!loadLegendsData()) {
		logWarningFormat("[LEGENDS] autotest: %s", gLegends.mError.c_str());
		return 0;
	}
	gLegends.mIsAutotest = 1;
	gLegends.mSeed = 1;
	gLegends.mAutotestAttach = 1;
	gLegends.mAutotestInspect = 0;
	gLegends.mAutotestSetupTicks = 60;
	gLegends.mAutotestBan.clear();
	std::array<std::vector<std::string>, 2> sq;
	size_t a = 0;
	while (a < text.size()) {
		size_t b = text.find('\n', a);
		if (b == std::string::npos) b = text.size();
		std::string line = text.substr(a, b - a);
		a = b + 1;
		const auto eq = line.find('=');
		if (eq == std::string::npos) continue;
		auto key = line.substr(0, eq), val = line.substr(eq + 1);
		while (!key.empty() && isspace((unsigned char)key.back())) key.pop_back();
		while (!key.empty() && isspace((unsigned char)key.front())) key.erase(0, 1);
		if (key == "seed") gLegends.mSeed = strtoull(val.c_str(), nullptr, 10);
		else if (key == "inspect") gLegends.mAutotestInspect = atoi(val.c_str());
		else if (key == "setup.ticks") gLegends.mAutotestSetupTicks = std::max(60, atoi(val.c_str()));
		else if (key == "attach") gLegends.mAutotestAttach = atoi(val.c_str());
		else if (key == "p1" || key == "p2" || key == "ban.p1") {
			size_t c = 0;
			while (c <= val.size()) {
				size_t d = val.find(',', c);
				if (d == std::string::npos) d = val.size();
				std::string item = val.substr(c, d - c);
				while (!item.empty() && isspace((unsigned char)item.back())) item.pop_back();
				while (!item.empty() && isspace((unsigned char)item.front())) item.erase(0, 1);
				if (!item.empty()) {
					if (key == "ban.p1") gLegends.mAutotestBan.push_back(item);
					else sq[key == "p2"].push_back(item);
				}
				c = d + 1;
			}
		}
	}
	if (sq[0].size() != 3 || sq[1].size() != 3) {
		logWarning("[LEGENDS] autotest needs p1 and p2 with three .def paths each");
		return 0;
	}
	newMatch();
	for (int s = 0; s < 2; s++)
		for (int i = 0; i < 3; i++) fillMember(&gLegends.mMatch->squad[s].members[i], sq[s][i]);
	gLegends.mMatch->coach[0].bannedCards = gLegends.mAutotestBan;
	for (const auto& id : gLegends.mAutotestBan) gLegends.mMatch->logf("autotest ban side 0: %s", id.c_str());
	gLegends.mMatch->logf("autotest seed %llu attach %d", (unsigned long long)gLegends.mSeed, gLegends.mAutotestAttach);
	gLegends.mMatch->dealOpening(0);
	gLegends.mMatch->dealOpening(1);
	gLegends.mMatch->cpuChooseOpening(1);
	// started from the title screen's first update, the way a player enters the mode (booting
	// straight into the Legends screen crashed Vita3K, see reports/legends-status.md)
	gLegends.mIsAutotestPending = 1;
	return 0;
}

int startPendingLegendsAutotest() {
	if (!gLegends.mIsAutotestPending) return 0;
	gLegends.mIsAutotestPending = 0;
	showLegendsScreen(LegendsScreenMode::Setup);
	return 1;
}

// ------------------------------------------------------------------ in-fight actor
static struct {
	MugenSpriteFile mSprites;
	MugenAnimations mAir;
	std::map<std::pair<int, int>, MugenAnimation*> mSpriteCache;
	std::vector<MugenAnimation*> mAnimations;
	int mTick = 0;               // combat ticks this bout (mode clock)
	int mFrame = 0;
	std::array<int, 2> mLastLife{{0, 0}};
	std::array<bool, 2> mWasLying{{false, false}};
	std::array<int, 2> mOwnStrain{{0, 0}};
	int mKOSeenAt = -1;
	int mEndRequested = 0;
	int mEndAt = -1;
	int mStartRound = 1;
	// HUD
	std::array<MugenAnimationHandlerElement*, 3> mTiles{}, mIcons{}, mPips{}, mThumbs{};
	std::array<int, 3> mTileGroup{{-1, -1, -1}}, mLastUid{{0, 0, 0}};
	std::array<int, 3> mTileName{{-1, -1, -1}}, mTileState{{-1, -1, -1}};
	std::array<const legends::CardDef*, 3> mShown{};
	MugenAnimationHandlerElement *mFocus = nullptr, *mArmed = nullptr, *mHypeFill = nullptr, *mInspect = nullptr;
	int mTicketText = -1, mClockText = -1, mCpuText = -1, mBannerText = -1, mBannerSub = -1;
	MugenAnimationHandlerElement* mBanner = nullptr;
	MugenAnimationHandlerElement* mSpark = nullptr;
	int mSparkUntil = 0;
	std::array<std::array<int, 3>, 2> mSquadShown{{{{-1, -1, -1}}, {{-1, -1, -1}}}};
	int mBannerUntil = 0;
	std::array<int, 2> mAwakeText{{-1, -1}};
	std::array<std::array<MugenAnimationHandlerElement*, 3>, 2> mSquadPips{};
	MugenAnimationHandlerElement* mInspectFace = nullptr;
	const legends::CardDef* mInspectShown = nullptr;
	std::array<MugenAnimationHandlerElement*, 2> mAuras{}, mHeals{};
	std::array<int, 2> mHealUntil{{0, 0}}, mAuraKind{{143, 143}};
	std::array<MugenAnimationHandlerElement*, 3> mDrawSparks{};
	std::array<int, 3> mDrawUntil{{0, 0, 0}};
	int mInspectTitle = -1, mInspectBody = -1, mInspectState = -1;
	int mFocusSlot = 0;
	int mDiscardHeld = 0;
	struct Echo { int id; MugenAnimationHandlerElement* e; float x, y, halfWidth, halfHeight; bool right; };
	std::vector<Echo> mEchoes;
	// telemetry: does the Resolve change behaviour? (section 13, step 3)
	std::array<int, 2> mCloseTicks{{0, 0}}, mCommands{{0, 0}}, mTaggedCommands{{0, 0}};
	float mDistanceSum = 0;
} gFight;

// above the power bars (y 226); docs/legends-design.md section 10 suggests y 207, which sits on them
static const float DOCK_Y = 188, DOCK_X[3] = {14, 117, 220}, HYPE_X = 85, HYPE_Y = 183;

static MugenAnimationHandlerElement* fightSprite(int g, int i, float x, float y, float z) {
	return addSprite(&gFight.mSprites, &gFight.mAnimations, g, i, x, y, z);
}

static MugenAnimation* fightFrame(int g, int i) {
	auto key = std::make_pair(g, i);
	auto it = gFight.mSpriteCache.find(key);
	if (it != gFight.mSpriteCache.end()) return it->second;
	auto* a = createOneFrameMugenAnimationForSprite(g, i);
	gFight.mSpriteCache[key] = a;
	gFight.mAnimations.push_back(a);
	return a;
}

static MugenAnimationHandlerElement* fightAction(int action, float x, float y, float z) {
	if (!hasMugenAnimation(&gFight.mAir, action)) return nullptr;
	auto* e = addMugenAnimation(getMugenAnimation(&gFight.mAir, action), &gFight.mSprites, Vector3D(x, y, z));
	setMugenAnimationBaseDrawScale(e, ART_SCALE);
	return e;
}

static void restartAction(MugenAnimationHandlerElement* e, int action) {
	if (!e) return;
	changeMugenAnimation(e, getMugenAnimation(&gFight.mAir, action));
	setMugenAnimationVisibility(e, 1);
}

static int fightText(const std::string& t, float x, float y, int font, MugenTextAlignment a, ColorF c, float z = 75) {
	return addText(t, x, y, font, a, c, z);
}

static void loadLegendsFight(void*) {
	gFight = decltype(gFight)();
	gFight.mSprites = loadMugenSpriteFileWithoutPalette(getDolmexicaAssetFolder() + "data/legends/legends.sff");
	gFight.mAir = loadMugenAnimationFile(getDolmexicaAssetFolder() + "data/legends/legends.air");
	gFight.mLastLife = {{getPlayerLife(getRootPlayer(0)), getPlayerLife(getRootPlayer(1))}};
	gFight.mStartRound = getDreamRoundNumber();
	for (int i = 0; i < 3; i++) {
		gFight.mTiles[i] = fightSprite(SPR_EMPTY, 0, DOCK_X[i], DOCK_Y, 70);
		gFight.mIcons[i] = fightSprite(SPR_ICON, 0, DOCK_X[i] + 6, DOCK_Y + 5, 72);
		gFight.mThumbs[i] = fightSprite(101, 0, DOCK_X[i] + 2, DOCK_Y + 2, 72);
		gFight.mDrawSparks[i] = fightAction(145, DOCK_X[i] + 34, DOCK_Y + 1, 74);
		if (gFight.mDrawSparks[i]) setMugenAnimationVisibility(gFight.mDrawSparks[i], 0);
		gFight.mPips[i] = fightSprite(SPR_PIPS, 0, DOCK_X[i] + 2, DOCK_Y + 20, 72); // under the icon, in the art window
		if (gFight.mThumbs[i]) setMugenAnimationVisibility(gFight.mThumbs[i], 0);
		setMugenAnimationVisibility(gFight.mIcons[i], 0);
		setMugenAnimationVisibility(gFight.mPips[i], 0);
		gFight.mTileName[i] = fightText(" ", DOCK_X[i] + 25, DOCK_Y + 12, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_LEFT, WHITE, 73);
		gFight.mTileState[i] = fightText(" ", DOCK_X[i] + 25, DOCK_Y + 22, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_LEFT, GREY, 73);
	}
	gFight.mFocus = fightAction(125, DOCK_X[0] - 2, DOCK_Y - 2, 74);
	gFight.mArmed = fightSprite(SPR_ARMED, 0, DOCK_X[0], DOCK_Y, 74);
	if (gFight.mArmed) setMugenAnimationVisibility(gFight.mArmed, 0);
	fightSprite(SPR_HYPE, 0, HYPE_X, HYPE_Y, 70);
	gFight.mHypeFill = fightSprite(SPR_HYPE, 1, HYPE_X, HYPE_Y, 71);
	fightText("HYPE", HYPE_X - 3, HYPE_Y + 5, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_RIGHT, ORANGE, 72);
	gFight.mTicketText = fightText(" ", HYPE_X + 153, HYPE_Y + 5, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_LEFT, ORANGE, 72);
	gFight.mClockText = fightText(" ", 160, 40, FIGHT_FONT_SMALL, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE, 72);
	gFight.mCpuText = fightText(" ", 312, 52, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_RIGHT, SIDE_COLOR[1], 72);
	for (int s = 0; s < 2; s++) {
		gFight.mAuras[s] = fightAction(143, 0, 0, 68);
		gFight.mHeals[s] = fightAction(142, 0, 0, 69);
		if (gFight.mAuras[s]) setMugenAnimationVisibility(gFight.mAuras[s], 0);
		if (gFight.mHeals[s]) setMugenAnimationVisibility(gFight.mHeals[s], 0);
		gFight.mAwakeText[s] = fightText(" ", s ? 284 : 36, 42, FIGHT_FONT_XS, s ? MUGEN_TEXT_ALIGNMENT_RIGHT : MUGEN_TEXT_ALIGNMENT_LEFT, FAMILY_COLOR[2], 72);
		for (int i = 0; i < 3; i++) gFight.mSquadPips[s][i] = fightSprite(SPR_SQUAD, 0, s ? 296 - i * 7 : 18 + i * 7, 36, 72);
	}
	gFight.mSpark = fightSprite(SPR_SPARK, 0, 0, 0, 69);
	if (gFight.mSpark) setMugenAnimationVisibility(gFight.mSpark, 0);
	gFight.mBanner = fightSprite(SPR_BANNER, 0, 80, 62, 76);
	if (gFight.mBanner) setMugenAnimationVisibility(gFight.mBanner, 0);
	gFight.mBannerText = fightText(" ", 160, 74, FIGHT_FONT_MED, MUGEN_TEXT_ALIGNMENT_CENTER, WHITE, 77);
	gFight.mBannerSub = fightText(" ", 160, 84, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_CENTER, GREY, 77);
	gFight.mInspect = fightSprite(SPR_INSPECT, 0, 30, 80, 78);
	if (gFight.mInspect) setMugenAnimationVisibility(gFight.mInspect, 0);
	gFight.mInspectFace = fightSprite(100, 0, 38, 80, 78);
	if (gFight.mInspectFace) setMugenAnimationVisibility(gFight.mInspectFace, 0);
	gFight.mInspectTitle = fightText(" ", 112, 94, FIGHT_FONT_SMALL, MUGEN_TEXT_ALIGNMENT_LEFT, WHITE, 79);
	gFight.mInspectBody = fightText(" ", 112, 106, FIGHT_FONT_RULES, MUGEN_TEXT_ALIGNMENT_LEFT, GREY, 79);
	setMugenTextTextBoxWidth(gFight.mInspectBody, 172);
	gFight.mInspectState = fightText(" ", 112, 173, FIGHT_FONT_XS, MUGEN_TEXT_ALIGNMENT_LEFT, ORANGE, 79);
	gHasPendingResult = 0;
}

static void unloadLegendsFight(void*) {
	// the screen's handlers free the elements and texts; only our sprite file and animations are ours
	unloadMugenSpriteFile(&gFight.mSprites);
	for (auto* a : gFight.mAnimations) destroyMugenAnimation(a);
	gFight.mAnimations.clear();
	gFight.mSpriteCache.clear();
	unloadMugenAnimationFile(&gFight.mAir);
	gFight.mEchoes.clear();
}

static bool inGuardState(DreamPlayer* p) {
	const int s = getPlayerState(p);
	return s >= 120 && s <= 155; // the common1.cns guard states every character inherits
}

static legends::CombatSnapshot makeSnapshot(int tCombatActive) {
	legends::CombatSnapshot s;
	s.tick = gFight.mTick;
	s.combatActive = tCombatActive != 0;
	for (int i = 0; i < 2; i++) {
		DreamPlayer* p = getRootPlayer(i);
		auto& f = s.f[i];
		f.alive = isPlayerAlive(p) != 0;
		f.life = getPlayerLife(p);
		f.lifeMax = getPlayerLifeMax(p);
		f.grounded = getPlayerStateType(p) != MUGEN_STATE_TYPE_AIR;
		// a legal opening: the fighter has control, or is idle (not attacking, not being hit). CPU
		// fighters rarely hold ctrl while the AI keeps them moving, so ctrl alone almost never opens
		f.control = getPlayerControl(p) != 0 || getPlayerStateMoveType(p) == MUGEN_STATE_MOVE_TYPE_IDLE;
		f.guarding = inGuardState(p);
		f.x = getPlayerPositionX(p, 320);
		f.y = getPlayerPositionY(p, 320);
		f.facingRight = getPlayerIsFacingRight(p) != 0;
		// a hit = life lost to something other than our own card strain
		f.gotHit = f.life < gFight.mLastLife[i] - gFight.mOwnStrain[i];
		const bool lying = getPlayerStateType(p) == MUGEN_STATE_TYPE_LYING;
		f.knockedDown = lying && !gFight.mWasLying[i];
		gFight.mWasLying[i] = lying;
		gFight.mLastLife[i] = f.life;
		gFight.mOwnStrain[i] = 0;
	}
	return s;
}

static void showBanner(int tSide, const std::string& tText, const std::string& tSub) {
	if (gFight.mBanner) setMugenAnimationVisibility(gFight.mBanner, 1);
	changeMugenText(gFight.mBannerText, tText.c_str());
	setMugenTextColorRGB(gFight.mBannerText, SIDE_COLOR[tSide].r, SIDE_COLOR[tSide].g, SIDE_COLOR[tSide].b);
	changeMugenText(gFight.mBannerSub, tSub.c_str());
	gFight.mBannerUntil = gFight.mFrame + 50;
}

static void applyActions(const std::vector<legends::Action>& tActions) {
	auto& m = *gLegends.mMatch;
	const float offX = getPlayerScreenPositionX(getRootPlayer(0), 320) - getPlayerPositionX(getRootPlayer(0), 320);
	const float offY = getPlayerScreenPositionY(getRootPlayer(0), 320) - getPlayerPositionY(getRootPlayer(0), 320);
	for (auto& a : tActions) {
		switch (a.kind) {
		case legends::ActionKind::Damage: {
			DreamPlayer* p = getRootPlayer(a.side);
			if (!isPlayerAlive(p)) break; // never hit or resurrect a fighter already marked KO
			if (a.text == "strain") gFight.mOwnStrain[a.side] += a.amount;
			addPlayerDamage(p, a.text == "strain" ? p : getRootPlayer(1 - a.side), a.amount);
			if (a.text != "strain" && gFight.mSpark) {
				setMugenAnimationPosition(gFight.mSpark, Vector3D(a.x + offX - 10, a.y + offY - 10, 69));
				setMugenAnimationVisibility(gFight.mSpark, 1);
				gFight.mSparkUntil = gFight.mFrame + 8;
			}
			break;
		}
		case legends::ActionKind::Heal: {
			DreamPlayer* p = getRootPlayer(a.side);
			if (isPlayerAlive(p)) {
				addPlayerLife(p, p, a.amount);
				restartAction(gFight.mHeals[a.side], 142);
				gFight.mHealUntil[a.side] = gFight.mFrame + 16;
			}
			showBanner(a.side, "RECOVERED", "+" + std::to_string(a.amount) + " HP");
			break;
		}
		case legends::ActionKind::EchoSpawn: {
			const int item = a.text == "chidori" ? 1 : 0;
			auto* e = fightAction(item ? 141 : 140, a.x + offX, a.y + offY, 69);
			if (e) setMugenAnimationFaceDirection(e, getPlayerIsFacingRight(getRootPlayer(a.side)));
			gFight.mEchoes.push_back({a.echoId, e, a.x, a.y, item ? 24.f : 16.f, item ? 16.f : 8.f, getPlayerIsFacingRight(getRootPlayer(a.side)) != 0});
			break;
		}
		case legends::ActionKind::EchoMove:
		case legends::ActionKind::EchoEnd:
			for (auto it = gFight.mEchoes.begin(); it != gFight.mEchoes.end(); ++it) {
				if (it->id != a.echoId) continue;
				it->x = a.x;
				it->y = a.y;
				if (a.kind == legends::ActionKind::EchoEnd) {
					if (it->e) removeMugenAnimation(it->e);
					gFight.mEchoes.erase(it);
				}
				break;
			}
			break;
		case legends::ActionKind::Log:
			if (const auto* d = m.catalog->find(a.text)) showBanner(a.side, d->name, a.side ? "CPU COACH" : legends::familyName(d->family));
			else if (a.text == "interrupted") showBanner(a.side, "INTERRUPTED", "THE CARD IS LOST");
			else if (a.text == "blocked") showBanner(1 - a.side, "BLOCKED", "");
			break;
		}
	}
	for (auto& echo : gFight.mEchoes) {
		if (echo.e) setMugenAnimationPosition(echo.e, Vector3D(echo.x + offX + (echo.right ? -echo.halfWidth : echo.halfWidth), echo.y + offY - echo.halfHeight, 69));
	}
}

static void endBoutSoon(const legends::BoutResult& r, int tDelay) {
	gPendingResult = r;
	gHasPendingResult = 1;
	gFight.mEndAt = gFight.mFrame + tDelay;
}

static void forcedEnd(void*) { stopFightScreenWin(); }

static void updateHud() {
	auto& m = *gLegends.mMatch;
	auto& c = m.coach[0];
	for (int i = 0; i < 3; i++) {
		const auto& h = c.hand[i];
		if (h.def != gFight.mShown[i]) { // a card arrived or left: swap the tile art
			gFight.mShown[i] = h.def;
			if (!gFight.mThumbs[i]) changeMugenAnimation(gFight.mTiles[i], fightFrame(h.empty() ? SPR_EMPTY : SPR_TILE, h.empty() ? 0 : int(h.def->family)));
			if (gFight.mThumbs[i]) {
				if (!h.empty()) changeMugenAnimation(gFight.mThumbs[i], fightFrame(101, cardArtIndex(h.def)));
				setMugenAnimationVisibility(gFight.mThumbs[i], !h.empty());
			}
			auto* icon = fightFrame(SPR_ICON, h.empty() ? 0 : int(h.def->family));
			changeMugenAnimation(gFight.mIcons[i], icon);
			setMugenAnimationVisibility(gFight.mIcons[i], !h.empty() && !gFight.mThumbs[i]);
			auto* pips = fightFrame(SPR_PIPS, h.empty() ? 0 : int(h.def->rarity));
			changeMugenAnimation(gFight.mPips[i], pips);
			setMugenAnimationVisibility(gFight.mPips[i], !h.empty());
			changeMugenText(gFight.mTileName[i], h.empty() ? " " : h.def->shortName.c_str());
		}
		if (gFight.mThumbs[i]) {
			const int group = h.empty() ? 124 : h.state == legends::CardState::Armed ? 121 : c.cooldown > 0 ? 122 : 120;
			if (group != gFight.mTileGroup[i]) {
				changeMugenAnimation(gFight.mTiles[i], fightFrame(group, 0));
				gFight.mTileGroup[i] = group;
			}
		}
		if (!h.empty() && h.uid != gFight.mLastUid[i]) {
			restartAction(gFight.mDrawSparks[i], 145);
			gFight.mDrawUntil[i] = gFight.mFrame + 12;
		}
		gFight.mLastUid[i] = h.empty() ? 0 : h.uid;
		if (gFight.mDrawSparks[i] && gFight.mFrame >= gFight.mDrawUntil[i]) setMugenAnimationVisibility(gFight.mDrawSparks[i], 0);
		static const char* KEY[3] = {"SQR", "TRI", "CIR"};
		std::string st;
		if (h.empty()) st = c.tickets.empty() ? "" : "DRAWING...";
		else if (h.state == legends::CardState::Armed) st = h.reason.empty() ? "ARMED" : h.reason;
		else if (c.cooldown > 0) st = std::string(KEY[i]) + "  WAIT " + std::to_string((c.cooldown + 59) / 60);
		else st = std::string(KEY[i]) + "  READY";
		changeMugenText(gFight.mTileState[i], st.empty() ? " " : st.c_str());
	}
	if (gFight.mArmed) {
		setMugenAnimationVisibility(gFight.mArmed, c.armedSlot >= 0);
		if (c.armedSlot >= 0) setMugenAnimationPosition(gFight.mArmed, Vector3D(DOCK_X[c.armedSlot], DOCK_Y, 74));
	}
	if (gFight.mFocus) setMugenAnimationPosition(gFight.mFocus, Vector3D(DOCK_X[gFight.mFocusSlot] - 2, DOCK_Y - 2, 74));
	if (gFight.mHypeFill) setMugenAnimationRectangleWidth(gFight.mHypeFill, std::max(1, int(300.0f * c.hype / m.catalog->hypeMax)));
	changeMugenText(gFight.mTicketText, c.tickets.empty() ? " " : ("+" + std::to_string(c.tickets.size())).c_str());
	const int left = std::max(0, m.boutTickLimit - gFight.mTick);
	changeMugenText(gFight.mClockText, std::to_string((left + 59) / 60).c_str());
	changeMugenText(gFight.mCpuText, ("CPU HAND " + std::to_string(m.coach[1].handCount())).c_str());
	for (int s = 0; s < 2; s++) {
		const int t = m.awakeningTicksLeft(s);
		auto* p = getRootPlayer(s);
		const float px = getPlayerScreenPositionX(p, 320), py = getPlayerScreenPositionY(p, 320);
		if (gFight.mAuras[s]) {
			const int kind = m.awakeningName(s) == "PLUS ULTRA" ? 144 : 143;
			if (t > 0 && kind != gFight.mAuraKind[s] && hasMugenAnimation(&gFight.mAir, kind)) {
				restartAction(gFight.mAuras[s], kind);
				gFight.mAuraKind[s] = kind;
			}
			setMugenAnimationVisibility(gFight.mAuras[s], t > 0 && isPlayerAlive(p));
			setMugenAnimationPosition(gFight.mAuras[s], Vector3D(px - 32, py - 90, 68));
		}
		if (gFight.mHeals[s]) {
			setMugenAnimationVisibility(gFight.mHeals[s], gFight.mFrame < gFight.mHealUntil[s] && isPlayerAlive(p));
			setMugenAnimationPosition(gFight.mHeals[s], Vector3D(px - 8, py - 36, 69));
		}
		char b[64];
		snprintf(b, sizeof(b), "%s %d.%d", m.awakeningName(s).c_str(), t / 60, (t % 60) / 6);
		changeMugenText(gFight.mAwakeText[s], t > 0 ? b : " ");
		for (int i = 0; i < 3; i++) {
			const auto& mem = m.squad[s].members[i];
			auto* e = gFight.mSquadPips[s][i];
			const int want = mem.eliminated ? 2 : i == m.squad[s].active ? 0 : 1;
			if (!e || gFight.mSquadShown[s][i] == want) continue;
			gFight.mSquadShown[s][i] = want;
			auto* anim = fightFrame(SPR_SQUAD, want);
			changeMugenAnimation(e, anim);
		}
	}
	// inspection (L held): full rules of the focused card, D-pad moves the focus
	const bool inspect = hasPressedLSingle(0) != 0 || (gLegends.mIsAutotest && gLegends.mAutotestInspect);
		if (gLegends.mIsAutotest && gLegends.mAutotestInspect && c.hand[gFight.mFocusSlot].empty())
		for (int i = 0; i < 3; ++i) if (!c.hand[i].empty()) { gFight.mFocusSlot = i; break; }
	const auto& fc = c.hand[gFight.mFocusSlot];
	if (gFight.mInspect) setMugenAnimationVisibility(gFight.mInspect, inspect && !fc.empty());
	if (gFight.mInspectFace) {
		setMugenAnimationVisibility(gFight.mInspectFace, inspect && !fc.empty());
		if (!fc.empty() && fc.def != gFight.mInspectShown) {
			changeMugenAnimation(gFight.mInspectFace, fightFrame(100, cardArtIndex(fc.def)));
			gFight.mInspectShown = fc.def;
		}
	}
	changeMugenText(gFight.mInspectTitle, inspect && !fc.empty() ? fc.def->name.c_str() : " ");
	changeMugenText(gFight.mInspectBody, inspect && !fc.empty() ? (std::string(legends::familyName(fc.def->family)) + " / " + legends::rarityName(fc.def->rarity) + ": " + fc.def->text).c_str() : " ");
	changeMugenText(gFight.mInspectState, inspect && !fc.empty() ? (fc.reason.empty() ? "HOLD R: DISCARD" : fc.reason).c_str() : " ");
	if (gFight.mSpark && gFight.mFrame > gFight.mSparkUntil) setMugenAnimationVisibility(gFight.mSpark, 0);
	if (gFight.mBanner && gFight.mFrame > gFight.mBannerUntil) {
		setMugenAnimationVisibility(gFight.mBanner, 0);
		changeMugenText(gFight.mBannerText, " ");
		changeMugenText(gFight.mBannerSub, " ");
	}
}

static void updateLegendsFight(void*) {
	if (!gLegends.mMatch || !gLegends.mIsBoutActive) return;
	auto& m = *gLegends.mMatch;
	gFight.mFrame++;
	// ends the engine decides (KO, win pose) arrive through boutFinished; these are ours
	if (gFight.mEndAt >= 0 && gFight.mFrame >= gFight.mEndAt && !gFight.mEndRequested) {
		gFight.mEndRequested = 1;
		addFadeOut(20, forcedEnd, NULL);
	}
	const int fighting = getDreamRoundStateNumber() == 2 && !isWrapperPaused();
	auto s = makeSnapshot(fighting && !gHasPendingResult);

	// KO: let this tick's hits settle, then decide on the next tick (section 3)
	if (!gHasPendingResult && (!s.f[0].alive || !s.f[1].alive)) {
		if (gFight.mKOSeenAt < 0) gFight.mKOSeenAt = gFight.mFrame;
		else if (gFight.mFrame > gFight.mKOSeenAt) endBoutSoon(legends::judgeBout(s.f[0], s.f[1], false), 60 * 6);
	}
	// a double KO or draw makes the engine start another round: Legends bouts have one
	if (gHasPendingResult && getDreamRoundNumber() > gFight.mStartRound && gFight.mEndAt > gFight.mFrame + 2) gFight.mEndAt = gFight.mFrame + 1;

	if (s.combatActive) {
		// human coach: Square / Triangle / Circle play the visible cards (section 10)
		if (!m.coach[0].isCpu && !hasPressedLSingle(0)) {
			const int pressed = hasPressedXFlankSingle(0) ? 0 : hasPressedYFlankSingle(0) ? 1 : hasPressedBFlankSingle(0) ? 2 : -1;
			if (pressed >= 0) {
				gFight.mFocusSlot = pressed;
				const auto why = m.requestPlay(0, pressed, s);
				if (!why.empty() && why != "EMPTY") showBanner(0, why, m.coach[0].hand[pressed].empty() ? "" : m.coach[0].hand[pressed].def->shortName);
			}
		}
		if (!m.coach[0].isCpu && hasPressedLSingle(0)) {
			if (hasPressedLeftFlankSingle(0)) gFight.mFocusSlot = (gFight.mFocusSlot + 2) % 3;
			if (hasPressedRightFlankSingle(0)) gFight.mFocusSlot = (gFight.mFocusSlot + 1) % 3;
		}
		gFight.mDiscardHeld = (!m.coach[0].isCpu && hasPressedRSingle(0)) ? gFight.mDiscardHeld + 1 : 0;
		if (gFight.mDiscardHeld == 30) m.discard(0, gFight.mFocusSlot);

		applyActions(m.tick(s));
		gFight.mTick++;
		const float dist = std::fabs(s.f[0].x - s.f[1].x);
		gFight.mDistanceSum += dist;
		for (int i = 0; i < 2; i++) gFight.mCloseTicks[i] += dist < 40;
		if (gFight.mTick >= m.boutTickLimit && !gHasPendingResult) { // 90 s: HP fractions decide
			endBoutSoon(legends::judgeBout(s.f[0], s.f[1], true), 90);
			showBanner(0, "TIME", "LOWER HP SHARE LOSES");
		}
	}
	updateHud();
	if (gFight.mFrame % 60 == 0) flushLegendsLog();
}

// does the Resolve change behaviour? (section 13, step 3): compared across autotest runs
static void logBoutTelemetry() {
	gLegends.mMatch->logf("bout %d telemetry: avg distance %.0f, close %d%%, commands p0 %d (tagged %d) p1 %d (tagged %d), %d ticks",
		gLegends.mMatch->boutNumber, gFight.mTick ? gFight.mDistanceSum / gFight.mTick : 0.f, gFight.mTick ? gFight.mCloseTicks[0] * 100 / gFight.mTick : 0,
		gFight.mCommands[0], gFight.mTaggedCommands[0], gFight.mCommands[1], gFight.mTaggedCommands[1], gFight.mTick);
}

ActorBlueprint getLegendsFightHandler() {
	return makeActorBlueprint(loadLegendsFight, unloadLegendsFight, updateLegendsFight);
}

// ------------------------------------------------------------------ hooks
static int sideOf(DreamPlayer* p) {
	if (!p) return -1;
	DreamPlayer* r = getPlayerRoot(p);
	return r ? r->mRootID : -1;
}

int getLegendsAIProfile(int tRootID, LegendsAIProfile* o) {
	if (getGameMode() != GAME_MODE_LEGENDS || !gLegends.mMatch || !gLegends.mIsBoutActive || tRootID < 0 || tRootID > 1) return 0;
	auto& m = *gLegends.mMatch;
	const auto p = m.profileFor(tRootID);
	if (!p.active) return 0;
	o->approachDistance = p.approachDistance;
	o->stopDistance = p.stopDistance;
	o->guardBias = p.guardBias;
	o->commandIntervalScale = p.commandIntervalScale;
	o->tagBias = p.tagBias;
	o->taggedCommands.clear();
	const auto& mem = m.squad[tRootID].members[m.squad[tRootID].active];
	if (const auto* a = legends::findAdapter(gLegends.mAdapters, mem.path)) {
		for (auto& tag : p.preferredTags) {
			auto it = a->tags.find(tag);
			if (it != a->tags.end()) o->taggedCommands.insert(o->taggedCommands.end(), it->second.begin(), it->second.end());
		}
	}
	return 1;
}

void noteLegendsAICommand(int tRootID, int tIsTagged) {
	if (getGameMode() != GAME_MODE_LEGENDS || tRootID < 0 || tRootID > 1) return;
	gFight.mCommands[tRootID]++;
	gFight.mTaggedCommands[tRootID] += tIsTagged != 0;
}

float getLegendsDamageScale(DreamPlayer* tAttacker, DreamPlayer* tDefender, int tIsGuarded) {
	if (getGameMode() != GAME_MODE_LEGENDS || !gLegends.mMatch || !gLegends.mIsBoutActive) return 1;
	const int a = sideOf(tAttacker), d = sideOf(tDefender);
	if (a < 0 || d < 0 || a == d) return 1;
	return gLegends.mMatch->attackFactor(a) * gLegends.mMatch->defenseFactor(d, !tIsGuarded);
}
