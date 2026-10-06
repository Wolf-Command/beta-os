import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else {
    fputs("usage: ggv_nota_vision_ocr <image>\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: args[1])
guard let img = NSImage(contentsOf: url),
      let tiff = img.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let cg = rep.cgImage else {
    fputs("could not load image\n", stderr)
    exit(1)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
req.recognitionLanguages = ["en-US", "id-ID"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([req])
    let lines = (req.results as? [VNRecognizedTextObservation] ?? [])
        .compactMap { $0.topCandidates(1).first?.string }
    print(lines.joined(separator: "\n"))
} catch {
    fputs("vision failed: \(error)\n", stderr)
    exit(1)
}
