// legendsmode.h -- the Legends mode inside Dolmexica (docs/legends-design.md).
//
// The rules live in legendscore.cpp; this file is the engine side: squad select, the opening
// deal, the relay of 1v1 bouts, the in-fight card HUD and input, and the hooks below that the
// AI (ai.cpp) and hit damage (playerdefinition.cpp) call. Every hook is a no-op unless the game
// mode is GAME_MODE_LEGENDS, so the classic modes keep their behaviour.
#pragma once

#include <string>
#include <vector>

#include <prism/actorhandler.h>

struct DreamPlayer;

void startLegendsMode();               // main menu entry (titlescreen.cpp, menu.itemname.legends)
int tryStartLegendsAutotest();         // initscreen.cpp: reads ux0:data/JFVT00001/legends_autotest.txt
int startPendingLegendsAutotest();     // titlescreen.cpp: starts that encounter from the title
prism::ActorBlueprint getLegendsFightHandler(); // fightscreen.cpp: HUD, card input and effects

// ai.cpp: coaching (CoachProfile) for a root player, 0 = no Legends coaching this tick
struct LegendsAIProfile {
	float approachDistance, stopDistance;
	float guardBias;               // added to the guard chance, which is then clamped to 15-85%
	float commandIntervalScale;
	float tagBias;                 // share of command picks taken from taggedCommands
	std::vector<std::string> taggedCommands; // adapter commands for the preferred tags
};
int getLegendsAIProfile(int tRootID, LegendsAIProfile* oProfile);
void noteLegendsAICommand(int tRootID, int tIsTagged);

// playerdefinition.cpp: multiplier for one hit's damage (card attack/defence modifiers)
float getLegendsDamageScale(DreamPlayer* tAttacker, DreamPlayer* tDefender, int tIsGuarded);
