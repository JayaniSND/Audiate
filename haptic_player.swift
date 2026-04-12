import AppKit
import Foundation

let args = CommandLine.arguments
let mode     = args.count > 1 ? args[1] : "mid"
let duration = args.count > 2 ? Double(args[2]) ?? 0.3 : 0.3

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

// Attack scaled to pitch — high notes get a sharp snap, low notes get a slow thud
func fireAttack(mode: String) {
    switch mode {
    case "very_high", "high":
        // 4 very rapid light taps — sharp percussive snap
        for i in 0..<4 {
            NSHapticFeedbackManager.defaultPerformer.perform(.alignment, performanceTime: .now)
            if i < 3 { Thread.sleep(forTimeInterval: 0.006) }
        }
    case "mid_high", "mid":
        // 3 medium clicks
        for i in 0..<3 {
            NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
            if i < 2 { Thread.sleep(forTimeInterval: 0.010) }
        }
    case "mid_low", "low", "very_low":
        // 2 slow heavy thuds — feels like a bow catching a low string
        for i in 0..<2 {
            NSHapticFeedbackManager.defaultPerformer.perform(.levelChange, performanceTime: .now)
            if i < 1 { Thread.sleep(forTimeInterval: 0.020) }
        }
    default:
        NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
    }
}

let (pattern, interval) = sustainConfig(mode: mode)

// Attack
fireAttack(mode: mode)

// Small gap so attack and sustain don't blur together
Thread.sleep(forTimeInterval: 0.015)

// Sustain
let attackTime   = 0.015 + (mode.contains("high") ? 0.030 : mode.contains("low") ? 0.055 : 0.040)
let sustainDuration = max(0, duration - attackTime)
let count = max(0, Int(sustainDuration / interval))

for i in 0..<count {
    NSHapticFeedbackManager.defaultPerformer.perform(pattern, performanceTime: .now)
    if i < count - 1 {
        Thread.sleep(forTimeInterval: interval)
    }
}