// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PaperTranslatorMac",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "PaperTranslatorMac", targets: ["PaperTranslatorMac"])
    ],
    targets: [
        .executableTarget(
            name: "PaperTranslatorMac",
            path: "Sources/PaperTranslatorMac"
        )
    ]
)
