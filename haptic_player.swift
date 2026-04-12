import AppKit
import Foundation

let args = CommandLine.arguments
let mode     = args.count > 1 ? args[1] : "mid"
let duration = args.count > 2 ? Double(args[2]) ?? 0.3 : 0.3
let legato   = args.count > 3 && args[3] == "1"

func sustainConfig(mode: String) -> (pattern: NSHapticFeedbackManager.FeedbackPattern, interval: Double) {
    switch mode {
    case "very_high": return (.alignment,   0.010)  // ~100hz — max buzz
    case "high":      return (.alignment,   0.018)  // ~55hz
    case "mid_high":  return (.generic,     0.030)  // ~33hz
    case "mid":       return (.generic,     0.055)  // ~18hz
    case "mid_low":   return (.levelChange, 0.090)  // ~11hz
    case "low":       return (.levelChange, 0.140)  // ~7hz
    case "very_low":  return (.levelChange, 0.200)  // ~5hz — slow distinct thuds
    default:          return (.generic,     0.055)
    }
}

// Single soft onset — one gentle pulse that matches the breathy start of a hum.
// Skipped entirely when legato=true (consecutive close-pitched notes).
func fireAttack(mode: String) {
    switch mode {
    case "very_high", "high":
        NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
        Thread.sleep(forTimeInterval: 0.010)
    case "mid_high", "mid":
        NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
        Thread.sleep(forTimeInterval: 0.015)
    case "mid_low", "low", "very_low":
        NSHapticFeedbackManager.defaultPerformer.perform(.levelChange, performanceTime: .now)
        Thread.sleep(forTimeInterval: 0.020)
    default:
        NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
        Thread.sleep(forTimeInterval: 0.015)
    }
}

let (pattern, interval) = sustainConfig(mode: mode)

// Attack (skipped for legato transitions)
if !legato {
    fireAttack(mode: mode)
}

// Small gap so attack and sustain don't blur together
Thread.sleep(forTimeInterval: legato ? 0.005 : 0.015)

// Sustain
// Attack is a single pulse — subtract the gap we already slept
let attackTime   = legato ? 0.005 : 0.015 + (mode.contains("high") ? 0.010 : mode.contains("low") ? 0.020 : 0.015)
let sustainDuration = max(0, duration - attackTime)
let count = max(0, Int(sustainDuration / interval))

for i in 0..<count {
    NSHapticFeedbackManager.defaultPerformer.perform(pattern, performanceTime: .now)
    if i < count - 1 {
        Thread.sleep(forTimeInterval: interval)
    }
}