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

// Constants for round time
const ROUND_TIMER = 115 // Round time starts at 1:55 (115 seconds)
const BOMB_TIMER = 45   // Bomb timer is usually 45 seconds after the bomb is planted

// KillEvent represents a kill event in the demo
type KillEvent struct {
	Time        string `json:"time"` // Time in the round (e.g., 1:23)
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
	Time      string     `json:"time"` // Time in the round (e.g., 1:23)
	Timestamp string     `json:"timestamp"`
	Player    string     `json:"player"`          // Player's name with team indicator
	PlayerPos [3]float32 `json:"player_position"` // Player's position (x, y, z)
	BombPlace string     `json:"bomb_place"`      // Where the bomb was planted or defused
	Action    string     `json:"action"`          // "plant" or "defuse"
	Success   bool       `json:"success"`         // Was the action successful?
}

// RoundInfo represents all events that happened in a specific round
type RoundInfo struct {
	RoundNumber   int            `json:"round_number"`
	TScore        int            `json:"t_score"`  // Score of Terrorists
	CTScore       int            `json:"ct_score"` // Score of Counter-Terrorists
	KillEvents    []KillEvent    `json:"kill_events"`
	BombEvents    []BombEvent    `json:"bomb_events"`
	GrenadeEvents []GrenadeEvent `json:"grenade_events"` // List of grenade events
	WeaponEvents  []WeaponEvent  `json:"weapon_events"`  // Weapons after freezetime
}

type GrenadeEvent struct {
	Time      string     `json:"time"` // Time in the round (e.g., 1:23)
	Timestamp string     `json:"timestamp"`
	Player    string     `json:"player"`          // Player's name with team indicator
	PlayerPos [3]float32 `json:"player_position"` // Player's position (x, y, z)
	Place     string     `json:"place"`           // Place where the grenade was thrown
	Grenade   string     `json:"grenade"`         // Type of grenade
}

// WeaponEvent represents the weapons a player has after the freezetime ends
type WeaponEvent struct {
	Player     string   `json:"player"`      // Player's name with team indicator
	Weapons    []string `json:"weapons"`     // List of weapons the player is holding
	Primary    string   `json:"primary"`     // Primary weapon (if available)
	Secondary  string   `json:"secondary"`   // Secondary weapon (if available)
	OtherEquip []string `json:"other_equip"` // Other equipment (grenades, etc.)
	MoneyLeft  int      `json:"money_left"`  // Player's remaining money after freezetime
}

// formatTime calculates and formats the time remaining in the round
func formatTime(roundStartTime, eventTime time.Duration, roundTimeRemaining int) string {
	// Calculate the time elapsed in seconds since the round started
	secondsElapsed := int(eventTime.Seconds() - roundStartTime.Seconds())
	remainingTime := roundTimeRemaining - secondsElapsed

	// Ensure that we don't go below zero (the round timer should not be negative)
	if remainingTime < 0 {
		remainingTime = 0
	}

	minutes := remainingTime / 60
	seconds := remainingTime % 60
	return fmt.Sprintf("%d:%02d", minutes, seconds)
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
	f, err := os.Open("faze-navi.dem") // Replace with your actual demo file path
	if err != nil {
		log.Panic("failed to open demo file: ", err)
	}
	defer f.Close()

	p := dem.NewParser(f)
	defer p.Close()

	var rounds []*RoundInfo           // Use a slice of pointers to track round data
	var currentRound *RoundInfo       // Pointer to track the current round
	var roundStartTime time.Duration  // To track when each round starts
	roundTimeRemaining := ROUND_TIMER // To track the round time remaining
	isBombPlanted := false            // To track whether the bomb is planted

	// Track round number manually
	roundNumber := 0

	// Register handler for the start of a round
	p.RegisterEventHandler(func(e events.RoundStart) {
		roundNumber++
		roundStartTime = p.CurrentTime() // Reset round start time to the current demo time
		log.Printf("New round started at %s", roundStartTime.String())
		roundTimeRemaining = ROUND_TIMER // Reset round time to 1:55
		isBombPlanted = false            // Reset bomb planted state at the start of a new round

		currentRound = &RoundInfo{
			RoundNumber: roundNumber,
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

			// Calculate time remaining in the round based on the round timer
			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			log.Printf("Elapsed time before kill %s", int(p.CurrentTime().Seconds()-roundStartTime.Seconds()), roundTimeRemaining)

			killEvent := KillEvent{
				Time:        elapsedTime, // Format time as MM:SS
				Timestamp:   p.CurrentTime().String(),
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
			// Calculate time remaining in the round
			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			// Bomb has been planted, set the bomb timer (usually 45 seconds)
			isBombPlanted = true // Track that the bomb is planted

			// Compute remaining time in the round after bomb plant
			bombPlantTime := int(p.CurrentTime().Milliseconds()-roundStartTime.Milliseconds()) / 1000
			roundTimeRemaining = bombPlantTime + BOMB_TIMER // Add 45 seconds after plant time

			bombEvent := BombEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
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

			// Calculate time remaining in the round
			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			bombEvent := BombEvent{
				Time:      elapsedTime, // Format time as MM:SS
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
			// Reset the timer to 115 seconds for the next round
			roundTimeRemaining = ROUND_TIMER
			currentRound.TScore = p.GameState().TeamTerrorists().Score()
			currentRound.CTScore = p.GameState().TeamCounterTerrorists().Score()
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

			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			grenadeEvent := GrenadeEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
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

			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			grenadeEvent := GrenadeEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
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

			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			grenadeEvent := GrenadeEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
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
			if e.Projectile.Thrower != nil {
				playerName = getPlayerNameWithTeam(e.Projectile.Thrower)
				place = e.Projectile.Thrower.LastPlaceName()
				playerPos = [3]float32{
					float32(e.Projectile.Thrower.Position().X),
					float32(e.Projectile.Thrower.Position().Y),
					float32(e.Projectile.Thrower.Position().Z),
				}
			}

			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			grenadeEvent := GrenadeEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
				Player:    playerName,
				PlayerPos: playerPos,
				Place:     place,
				Grenade:   "Molotov",
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

			elapsedTime := formatTime(roundStartTime, p.CurrentTime(), roundTimeRemaining)

			grenadeEvent := GrenadeEvent{
				Time:      elapsedTime, // Format time as MM:SS
				Timestamp: p.CurrentTime().String(),
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
					Player:     playerName,
					Weapons:    weapons,
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
