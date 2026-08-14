// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "KPaperMac",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "KPaperMac", targets: ["KPaperMac"])
    ],
    targets: [
        .executableTarget(
            name: "KPaperMac",
            path: "Sources/KPaperMac"
        )
    ]
)
