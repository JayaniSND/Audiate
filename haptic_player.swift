// /tmp/haptic_player.swift
import AppKit
import Foundation

// Read args: intensity count interval_seconds
// e.g. ./haptic_player generic 3 0.1
let args = CommandLine.arguments
let intensityStr = args.count > 1 ? args[1] : "generic"
let count        = args.count > 2 ? Int(args[2]) ?? 1 : 1
let interval     = args.count > 3 ? Double(args[3]) ?? 0.0 : 0.0

let pattern: NSHapticFeedbackManager.FeedbackPattern
switch intensityStr {
    case "alignment":   pattern = .alignment
    case "levelChange": pattern = .levelChange
    default:            pattern = .generic
}

for i in 0..<count {
    NSHapticFeedbackManager.defaultPerformer.perform(pattern, performanceTime: .now)
    if i < count - 1 && interval > 0 {
        Thread.sleep(forTimeInterval: interval)
    }
}