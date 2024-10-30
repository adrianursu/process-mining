package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	dem "github.com/markus-wa/demoinfocs-golang/v4/pkg/demoinfocs"
	common "github.com/markus-wa/demoinfocs-golang/v4/pkg/demoinfocs/common"
	events "github.com/markus-wa/demoinfocs-golang/v4/pkg/demoinfocs/events"
)

// KillEvent represents a kill event in the demo
type ChangeLocationEvent struct {
	Timestamp string `json:"timestamp"`
	Player    string `json:"player"`    // Player's name with team indicator
	OldPlace  string `json:"old_place"` // Old map location of the player
	NewPlace  string `json:"new_place"` // New map location of the player
}

var oldPlaceForPlayer = make(map[string]string)
var roundStarted = false

// KillEvent represents a kill event in the demo
type KillEvent struct {
	Timestamp   string `json:"timestamp"`
	Killer      string `json:"killer"`       // Killer's name with team indicator
	KillerPlace string `json:"killer_place"` // Map location of the killer
	Victim      string `json:"victim"`       // Victim's name with team indicator
	VictimPlace string `json:"victim_place"` // Map location of the victim
	Weapon      string `json:"weapon"`       // Weapon used
	Headshot    bool   `json:"headshot"`     // Was it a head-shot?
}

// BombEvent represents a bomb-related event (plant or defuse)
type BombEvent struct {
	Timestamp string     `json:"timestamp"`
	Player    string     `json:"player"`          // Player's name with team indicator
	PlayerPos [3]float32 `json:"player_position"` // Player's position (x, y, z)
	BombPlace string     `json:"bomb_place"`      // Where the bomb was planted or defused
	Action    string     `json:"action"`          // "plant" or "defuse"
	Success   bool       `json:"success"`         // Was the action successful?
}

// RoundInfo represents all events that happened in a specific round
type RoundInfo struct {
	RoundNumber          int                   `json:"round_number"`
	TScore               int                   `json:"t_score"`  // Score of Terrorists
	CTScore              int                   `json:"ct_score"` // Score of Counter-Terrorists
	Winner               string                `json:"winner"`
	Timestamp            string                `json:"timestamp"`
	EndTimestamp         string                `json:"end_timestamp"`
	EndReason            string                `json:"end_reason"`
	KillEvents           []KillEvent           `json:"kill_events"`
	ChangeLocationEvents []ChangeLocationEvent `json:"change_location_events"`
	BombEvents           []BombEvent           `json:"bomb_events"`
	GrenadeEvents        []GrenadeEvent        `json:"grenade_events"`     // List of grenade events
	WeaponEvents         []WeaponEvent         `json:"inventory_checking"` // Weapons after freezetime
}

type GrenadeEvent struct {
	Timestamp string     `json:"timestamp"`
	Player    string     `json:"player"`          // Player's name with team indicator
	PlayerPos [3]float32 `json:"player_position"` // Player's position (x, y, z)
	Place     string     `json:"place"`           // Place where the grenade was thrown
	Grenade   string     `json:"grenade"`         // Type of grenade
}

// WeaponEvent represents the weapons a player has after the freezetime ends
type WeaponEvent struct {
	Timestamp  string   `json:"timestamp"`
	Player     string   `json:"player"`      // Player's name with team indicator
	Primary    string   `json:"primary"`     // Primary weapon (if available)
	Secondary  string   `json:"secondary"`   // Secondary weapon (if available)
	OtherEquip []string `json:"other_equip"` // Other equipment (grenades, etc.)
	MoneyLeft  int      `json:"money_left"`  // Player's remaining money after freezetime
}

func DurationToISO8601(d time.Duration) string {
	totalMilliseconds := d.Milliseconds()
	hours := totalMilliseconds / 3600000
	minutes := (totalMilliseconds % 3600000) / 60000
	seconds := (totalMilliseconds % 60000) / 1000
	milliseconds := totalMilliseconds % 1000

	result := "1970-01-01T"

	result += fmt.Sprintf("%02d", hours)

	result += fmt.Sprintf(":%02d", minutes)

	result += fmt.Sprintf(":%02d", seconds)

	result += fmt.Sprintf(".%03d", milliseconds)

	return result
}

// getPlayerNameWithTeam returns the player's name appended with their team (e.g., "Player1 [T]" or "Player2 [CT]")
func getPlayerNameWithTeam(player *common.Player) string {
	if player == nil {
		return "Unknown"
	}
	if player.Team == common.TeamTerrorists {
		return fmt.Sprintf("%s [T]", player.Name)
	} else if player.Team == common.TeamCounterTerrorists {
		return fmt.Sprintf("%s [CT]", player.Name)
	}
	return player.Name
}

// Helper function to get the weapon's name
func getWeaponName(weapon *common.Equipment) string {
	if weapon != nil {
		return weapon.Type.String()
	}
	return "Unknown"
}

func main() {
	f, err := os.Open("demos/natus-vincere-vs-mouz-m1-inferno.dem") // Replace with your actual demo file path
	if err != nil {
		log.Panic("failed to open demo file: ", err)
	}
	defer f.Close()

	p := dem.NewParser(f)
	defer p.Close()

	var rounds []*RoundInfo          // Use a slice of pointers to track round data
	var currentRound *RoundInfo      // Pointer to track the current round
	var roundStartTime time.Duration // To track when each round starts
	isBombPlanted := false           // To track whether the bomb is planted

	// Track round number manually
	roundNumber := 0

	// Register handler for the start of a round
	p.RegisterEventHandler(func(e events.RoundStart) {
		roundNumber++
		roundStartTime = p.CurrentTime() // Reset round start time to the current demo time
		roundStarted = true
		log.Printf("New round started at %s", roundStartTime.String())
		isBombPlanted = false // Reset bomb planted state at the start of a new round

		oldPlaceForPlayer = make(map[string]string)
		players := p.GameState().Participants().Playing()
		for _, player := range players {
			oldPlaceForPlayer[getPlayerNameWithTeam(player)] = ""
		}

		currentRound = &RoundInfo{
			RoundNumber: roundNumber,
			Timestamp:   DurationToISO8601(roundStartTime),
			TScore:      p.GameState().TeamTerrorists().Score(),
			CTScore:     p.GameState().TeamCounterTerrorists().Score(),
		}
		rounds = append(rounds, currentRound) // Append a pointer to the current round
	})

	// Register handler for kill events
	p.RegisterEventHandler(func(e events.Kill) {
		if currentRound != nil {
			// Get player names with team indicators (T or CT)
			killerName := getPlayerNameWithTeam(e.Killer)
			victimName := getPlayerNameWithTeam(e.Victim)

			killerPlace := ""
			victimPlace := ""

			// Get player positions on map call-outs
			if e.Killer != nil {
				killerPlace = e.Killer.LastPlaceName()
			}

			if e.Victim != nil {
				victimPlace = e.Victim.LastPlaceName()
			}

			killEvent := KillEvent{
				Timestamp:   DurationToISO8601(p.CurrentTime()),
				Killer:      killerName,
				KillerPlace: killerPlace,
				Victim:      victimName,
				VictimPlace: victimPlace,
				Weapon:      e.Weapon.String(),
				Headshot:    e.IsHeadshot,
			}
			currentRound.KillEvents = append(currentRound.KillEvents, killEvent)
		}
	})

	// Register handler for bomb plant events
	p.RegisterEventHandler(func(e events.BombPlanted) {
		if currentRound != nil {
			playerPos := [3]float32{}
			bombPlace := ""
			playerName := ""
			if e.Player != nil {
				playerName = getPlayerNameWithTeam(e.Player)
				bombPlace = e.Player.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Player.Position().X),
					float32(e.Player.Position().Y),
					float32(e.Player.Position().Z),
				}
			}

			bombEvent := BombEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				BombPlace: bombPlace,
				Action:    "plant",
				Success:   true,
			}
			currentRound.BombEvents = append(currentRound.BombEvents, bombEvent)
		}
	})

	// Register handler for bomb defuse events
	p.RegisterEventHandler(func(e events.BombDefused) {
		if currentRound != nil && isBombPlanted {
			playerName := getPlayerNameWithTeam(e.Player)
			playerPos := [3]float32{}
			if e.Player != nil {
				playerPos = [3]float32{
					float32(e.Player.Position().X),
					float32(e.Player.Position().Y),
					float32(e.Player.Position().Z),
				}
			}

			bombEvent := BombEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Action:    "defuse",
				Success:   true,
			}
			currentRound.BombEvents = append(currentRound.BombEvents, bombEvent)
		}
	})

	// Register handler for round end events to capture final scores
	p.RegisterEventHandler(func(e events.RoundEnd) {
		if currentRound != nil {
			roundStarted = false
			currentRound.EndTimestamp = DurationToISO8601(p.CurrentTime())

			switch e.Reason {
			case events.RoundEndReasonBombDefused:
				currentRound.EndReason = "BombDefused"
			case events.RoundEndReasonCTWin:
				currentRound.EndReason = "TEliminated"
			case events.RoundEndReasonCTSurrender:
				currentRound.EndReason = "CTSurrender"
			case events.RoundEndReasonTerroristsWin:
				currentRound.EndReason = "CTEliminated"
			case events.RoundEndReasonTerroristsSurrender:
				currentRound.EndReason = "TSurrender"
			case events.RoundEndReasonTargetBombed:
				currentRound.EndReason = "BombExploded"
			case events.RoundEndReasonTargetSaved:
				currentRound.EndReason = "TimeExpired"
			}

			if e.Winner == common.TeamTerrorists {
				currentRound.Winner = "T"
			} else {
				currentRound.Winner = "CT"
			}
		}
	})

	// Register handler for HE grenade explosion events (HE grenades explode, not thrown)
	p.RegisterEventHandler(func(e events.HeExplode) {
		if currentRound != nil {
			playerPos := [3]float32{}
			place := ""
			playerName := ""
			if e.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Thrower)
				place = e.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Thrower.Position().X),
					float32(e.Thrower.Position().Y),
					float32(e.Thrower.Position().Z),
				}
			}

			grenadeEvent := GrenadeEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Grenade:   "HE Grenade",
			}
			currentRound.GrenadeEvents = append(currentRound.GrenadeEvents, grenadeEvent)
		}
	})

	// Register handler for flashbang explosion events
	p.RegisterEventHandler(func(e events.FlashExplode) {
		if currentRound != nil {
			playerPos := [3]float32{}
			place := ""
			playerName := ""
			if e.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Thrower)
				place = e.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Thrower.Position().X),
					float32(e.Thrower.Position().Y),
					float32(e.Thrower.Position().Z),
				}
			}

			grenadeEvent := GrenadeEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Type:      "deployed",
				Grenade:   "Flashbang",
			}
			currentRound.GrenadeEvents = append(currentRound.GrenadeEvents, grenadeEvent)
		}
	})

	// Register handler for smoke grenade throw events
	p.RegisterEventHandler(func(e events.SmokeStart) {
		if currentRound != nil {
			playerPos := [3]float32{}
			place := ""
			playerName := ""
			if e.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Thrower)
				place = e.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Thrower.Position().X),
					float32(e.Thrower.Position().Y),
					float32(e.Thrower.Position().Z),
				}
			}

			grenadeEvent := GrenadeEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Grenade:   "Smoke Grenade",
			}
			currentRound.GrenadeEvents = append(currentRound.GrenadeEvents, grenadeEvent)
		}
	})

	// Register handler for Molotov/Incendiary grenade throw events
	p.RegisterEventHandler(func(e events.GrenadeProjectileThrow) {
		if currentRound != nil {
			playerPos := [3]float32{}
			place := ""
			playerName := ""

			if e.Projectile.WeaponInstance.String() != "Molotov" && e.Projectile.WeaponInstance.String() != "Incendiary Grenade" {
				return
			}

			if e.Projectile.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Projectile.Thrower)
				place = e.Projectile.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Projectile.Thrower.Position().X),
					float32(e.Projectile.Thrower.Position().Y),
					float32(e.Projectile.Thrower.Position().Z),
				}
			}

			grenadeEvent := GrenadeEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Grenade:   e.Projectile.WeaponInstance.String(),
			}
			currentRound.GrenadeEvents = append(currentRound.GrenadeEvents, grenadeEvent)
		}
	})

	// Register handler for decoy grenade throw events
	p.RegisterEventHandler(func(e events.DecoyStart) {
		if currentRound != nil {
			playerPos := [3]float32{}
			place := ""
			playerName := ""
			if e.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Thrower)
				place = e.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Thrower.Position().X),
					float32(e.Thrower.Position().Y),
					float32(e.Thrower.Position().Z),
				}
			}

			grenadeEvent := GrenadeEvent{
				Timestamp: DurationToISO8601(p.CurrentTime()),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Grenade:   "Decoy",
			}
			currentRound.GrenadeEvents = append(currentRound.GrenadeEvents, grenadeEvent)
		}
	})

	// Register handler for when freezetime ends
	p.RegisterEventHandler(func(e events.RoundFreezetimeEnd) {
		if currentRound != nil {
			weaponEvents := []WeaponEvent{}

			// Get all players from both teams (T and CT)
			for _, player := range p.GameState().Participants().Playing() {
				playerName := getPlayerNameWithTeam(player)

				// List to store the weapons the player is holding
				var weapons []string
				var primaryWeapon string
				var secondaryWeapon string
				var otherEquip []string

				// Loop through player's inventory and sort weapons into primary, secondary, and other equipment
				for _, weapon := range player.Weapons() {
					weapons = append(weapons, getWeaponName(weapon))

					// Classify weapons: primary, secondary, or other (grenades, etc.)
					switch weapon.Class() {
					case common.EqClassRifle, common.EqClassSMG, common.EqClassHeavy:
						primaryWeapon = getWeaponName(weapon)
					case common.EqClassPistols:
						secondaryWeapon = getWeaponName(weapon)
					default:
						otherEquip = append(otherEquip, getWeaponName(weapon))
					}
				}

				// Capture player's remaining money after the freezetime ends
				moneyLeft := player.Money()

				// Create a WeaponEvent for this player
				weaponEvent := WeaponEvent{
					Timestamp:  currentRound.Timestamp,
					Player:     playerName,
					Primary:    primaryWeapon,
					Secondary:  secondaryWeapon,
					OtherEquip: otherEquip,
					MoneyLeft:  moneyLeft,
				}
				weaponEvents = append(weaponEvents, weaponEvent)
			}

			// Add weapon events to the current round
			currentRound.WeaponEvents = weaponEvents
		}
	})

	// Verify each frame if location of player has changed and update delta
	p.RegisterEventHandler(func(e events.FrameDone) {
		if roundStarted {
			players := p.GameState().Participants().Playing()
			for _, player := range players {
				playerName := getPlayerNameWithTeam(player)
				if player == nil || !player.IsAlive() {
					continue
				}

				newPlace := player.LastPlaceName()
				oldPlace := oldPlaceForPlayer[playerName]
				if newPlace == oldPlace {
					continue
				}

				changeLocationEvent := ChangeLocationEvent{
					Timestamp: DurationToISO8601(p.CurrentTime()),
					Player:    playerName,
					OldPlace:  oldPlace,
					NewPlace:  newPlace,
				}

				oldPlaceForPlayer[playerName] = newPlace

				currentRound.ChangeLocationEvents = append(currentRound.ChangeLocationEvents, changeLocationEvent)
			}
		}
	})

	// Parse the demo until the end
	err = p.ParseToEnd()
	if err != nil {
		log.Panic("failed to parse demo: ", err)
	}

	// Convert all rounds and their events to JSON
	jsonData, err := json.MarshalIndent(rounds, "", "  ")
	if err != nil {
		log.Panic("failed to marshal rounds to JSON: ", err)
	}

	// Output the JSON to a file
	err = os.WriteFile("rounds_data.json", jsonData, 0644)
	if err != nil {
		log.Panic("failed to write rounds data to file: ", err)
	}

	fmt.Println("Round data exported to rounds_data.json")
}
