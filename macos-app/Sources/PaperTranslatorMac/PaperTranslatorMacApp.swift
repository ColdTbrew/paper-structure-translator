import AppKit
import Network
import SwiftUI
import UniformTypeIdentifiers

@main
struct PaperTranslatorMacApp: App {
    @StateObject private var model = TranslatorModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .frame(minWidth: 760, minHeight: 620)
        }
        .windowStyle(.titleBar)
    }
}

struct ContentView: View {
    @EnvironmentObject private var model: TranslatorModel
    @State private var isDropTargeted = false

    var body: some View {
        ZStack {
            glassBackground
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    HStack(alignment: .top, spacing: 18) {
                        VStack(spacing: 18) {
                            dropZone
                            clipboardPanel
                        }
                        .frame(maxWidth: .infinity)

                        VStack(spacing: 18) {
                            outputPanel
                            runtimePanel
                        }
                        .frame(width: 300)
                    }
                    settingsPanel
                    logPanel
                }
                .padding(24)
            }
        }
        .preferredColorScheme(.light)
    }

    private var glassBackground: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.98, green: 0.99, blue: 1.00),
                    Color(red: 0.94, green: 0.98, blue: 0.98),
                    Color(red: 0.99, green: 0.96, blue: 0.99)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            Circle()
                .fill(AppPalette.accentTeal.opacity(0.18))
                .frame(width: 360, height: 360)
                .blur(radius: 60)
                .offset(x: -330, y: -250)
            Circle()
                .fill(AppPalette.accentPurple.opacity(0.12))
                .frame(width: 300, height: 300)
                .blur(radius: 70)
                .offset(x: 360, y: -150)
            Circle()
                .fill(AppPalette.accentTeal.opacity(0.14))
                .frame(width: 320, height: 320)
                .blur(radius: 80)
                .offset(x: 280, y: 320)
            Circle()
                .fill(AppPalette.accentPink.opacity(0.12))
                .frame(width: 260, height: 260)
                .blur(radius: 70)
                .offset(x: -230, y: 300)
        }
        .ignoresSafeArea()
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 30, weight: .semibold))
                .foregroundStyle(AppPalette.accentTeal)
                .frame(width: 52, height: 52)
                .background(AppPalette.glassStrong, in: RoundedRectangle(cornerRadius: 8))
                .overlay(glassStroke(cornerRadius: 8))
            VStack(alignment: .leading, spacing: 2) {
                Text("Paper Translator")
                    .font(AppTypography.display(size: 28, weight: .bold))
                    .foregroundStyle(AppPalette.textPrimary)
                Text("PDF 드롭 또는 클립보드 HTML URL로 구조 보존 한국어 논문 뷰어를 생성합니다.")
                    .font(AppTypography.korean(size: 14, weight: .medium))
                    .foregroundStyle(AppPalette.textSecondary)
            }
            Spacer()
            if model.isRunning {
                ProgressView().controlSize(.small)
                Button {
                    model.cancel()
                } label: {
                    Label("중지", systemImage: "stop.fill")
                }
                .buttonStyle(GlassButtonStyle(kind: .secondary))
            }
        }
        .padding(20)
        .glassCard()
    }

    private var dropZone: some View {
        VStack(spacing: 10) {
            Image(systemName: "square.and.arrow.down")
                .font(.system(size: 34, weight: .medium))
                .foregroundStyle(isDropTargeted ? AppPalette.accentTeal : AppPalette.textSecondary)
            Text("PDF를 여기에 드래그 앤 드롭")
                .font(AppTypography.korean(size: 18, weight: .semibold))
                .foregroundStyle(AppPalette.textPrimary)
            Text("드롭하면 pdf-import -> translate -> restyle 순서로 실행합니다.")
                .font(AppTypography.korean(size: 14, weight: .medium))
                .foregroundStyle(AppPalette.textSecondary)
        }
        .frame(maxWidth: .infinity, minHeight: 150)
        .background(isDropTargeted ? AppPalette.accentTeal.opacity(0.14) : AppPalette.glass, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(isDropTargeted ? AppPalette.accentTeal.opacity(0.42) : AppPalette.border, style: StrokeStyle(lineWidth: 1.3, dash: [8, 5])))
        .shadow(color: AppPalette.shadow, radius: 18, y: 8)
        .onDrop(of: [UTType.fileURL.identifier], isTargeted: $isDropTargeted) { providers in
            model.handleDrop(providers: providers)
        }
    }

    private var clipboardPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("HTML URL 번역", systemImage: "link")
            VStack(alignment: .leading, spacing: 10) {
                Text("클립보드에 있는 arXiv/ar5iv HTML URL을 읽어서 fetch -> translate -> restyle을 실행합니다.")
                    .font(AppTypography.korean(size: 14, weight: .medium))
                    .foregroundStyle(AppPalette.textSecondary)
                HStack {
                    Button {
                        model.translateClipboardURL()
                    } label: {
                        Label("클립보드 URL 번역", systemImage: "doc.on.clipboard")
                    }
                    .buttonStyle(GlassButtonStyle(kind: .primary))
                    .disabled(model.isRunning)

                    Button {
                        model.loadClipboardPreview()
                    } label: {
                        Label("클립보드 확인", systemImage: "eye")
                    }
                    .buttonStyle(GlassButtonStyle(kind: .secondary))
                    .disabled(model.isRunning)

                    Text(model.clipboardPreview)
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .foregroundStyle(AppPalette.textSecondary)
                }
            }
        }
        .glassCard()
    }

    private var settingsPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("설정", systemImage: "slider.horizontal.3")
            Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 10) {
                GridRow {
                    Text("Repo")
                    TextField("paper-structure-translator 경로", text: $model.repoPath)
                        .textFieldStyle(GlassTextFieldStyle())
                    Button("저장") {
                        model.saveSettings()
                    }
                    .buttonStyle(GlassButtonStyle(kind: .secondary))
                }
                GridRow {
                    Text("Base URL")
                    TextField(".env를 쓰려면 비워두세요", text: $model.baseURLOverride)
                        .textFieldStyle(GlassTextFieldStyle())
                    Button("Doctor") {
                        model.runDoctor()
                    }
                    .buttonStyle(GlassButtonStyle(kind: .secondary))
                    .disabled(model.isRunning)
                }
                GridRow {
                    Text("API Key")
                    SecureField(".env를 쓰려면 비워두세요", text: $model.apiKeyOverride)
                        .textFieldStyle(GlassTextFieldStyle())
                    Text("앱에는 저장하지 않습니다.")
                        .font(AppTypography.korean(size: 12, weight: .regular))
                        .foregroundStyle(AppPalette.textTertiary)
                }
            }
            .foregroundStyle(AppPalette.textPrimary)
        }
        .glassCard()
    }

    private var outputPanel: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("결과", systemImage: "checkmark.seal")
            VStack(alignment: .leading, spacing: 4) {
                Text(model.statusText)
                    .font(AppTypography.korean(size: 18, weight: .semibold))
                    .foregroundStyle(AppPalette.textPrimary)
                Text(model.lastPaperID.isEmpty ? "아직 생성된 결과가 없습니다." : model.lastPaperID)
                    .font(AppTypography.korean(size: 12, weight: .regular))
                    .foregroundStyle(AppPalette.textSecondary)
            }
            VStack(spacing: 8) {
                Button {
                    model.openOutput(kind: .korean)
                } label: {
                    Label("한국어 열기", systemImage: "doc.text")
                }
                .buttonStyle(GlassButtonStyle(kind: .secondary))
                .disabled(model.lastPaperID.isEmpty)
                Button {
                    model.openOutput(kind: .bilingual)
                } label: {
                    Label("한영 병행 열기", systemImage: "rectangle.split.2x1")
                }
                .buttonStyle(GlassButtonStyle(kind: .secondary))
                .disabled(model.lastPaperID.isEmpty)
                Button {
                    model.openOutputsFolder()
                } label: {
                    Label("outputs 열기", systemImage: "folder")
                }
                .buttonStyle(GlassButtonStyle(kind: .secondary))
            }
        }
        .glassCard()
    }

    private var logPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionTitle("진행 로그", systemImage: "terminal")
            ScrollViewReader { proxy in
                ScrollView {
                    Text(model.logText.isEmpty ? "대기 중입니다." : model.logText)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(model.logText.isEmpty ? AppPalette.textTertiary : AppPalette.textPrimary)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .id("log-end")
                }
                .frame(minHeight: 190)
                .onChange(of: model.logText) { _ in
                    proxy.scrollTo("log-end", anchor: .bottom)
                }
            }
        }
        .glassCard()
    }

    private var runtimePanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle("Runtime", systemImage: "cpu")
            Label("SwiftUI native app", systemImage: "checkmark.circle")
            Label(".venv Python direct", systemImage: "checkmark.circle")
            Label("uv not used by app runtime", systemImage: "checkmark.circle")
            Text("번역 엔진은 기존 Python 파이프라인을 직접 실행합니다. `.venv`가 없으면 `scripts/bootstrap_python_env.sh`로 준비하세요.")
                .font(AppTypography.korean(size: 12, weight: .regular))
                .foregroundStyle(AppPalette.textSecondary)
        }
        .font(AppTypography.display(size: 12, weight: .medium))
        .foregroundStyle(AppPalette.textSecondary)
        .glassCard()
    }

    private func sectionTitle(_ text: String, systemImage: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: systemImage)
                .foregroundStyle(AppPalette.accentTeal)
            Text(text)
                .font(AppTypography.korean(size: 16, weight: .semibold))
                .foregroundStyle(AppPalette.textPrimary)
        }
    }
}

private enum AppPalette {
    static let textPrimary = Color(red: 0.11, green: 0.13, blue: 0.16)
    static let textSecondary = Color(red: 0.36, green: 0.40, blue: 0.46)
    static let textTertiary = Color(red: 0.55, green: 0.58, blue: 0.64)
    static let glass = Color.white.opacity(0.62)
    static let glassStrong = Color.white.opacity(0.78)
    static let border = Color.white.opacity(0.72)
    static let stroke = Color(red: 0.72, green: 0.78, blue: 0.84).opacity(0.38)
    static let shadow = Color(red: 0.18, green: 0.24, blue: 0.31).opacity(0.13)
    static let accentTeal = Color(red: 0.12, green: 0.58, blue: 0.54)
    static let accentBlue = Color(red: 0.12, green: 0.44, blue: 0.78)
    static let accentPurple = Color(red: 0.48, green: 0.30, blue: 0.75)
    static let accentPink = Color(red: 0.82, green: 0.24, blue: 0.52)
}

private enum AppTypography {
    static func display(size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .default)
    }

    static func korean(size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .custom("Apple SD Gothic Neo", size: size).weight(weight)
    }
}

private let glassFill = AppPalette.glass

private func glassStroke(cornerRadius: CGFloat = 8) -> some View {
    RoundedRectangle(cornerRadius: cornerRadius)
        .strokeBorder(AppPalette.stroke, lineWidth: 1)
}

private struct GlassCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(18)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 8))
            .background(glassFill, in: RoundedRectangle(cornerRadius: 8))
            .overlay(glassStroke(cornerRadius: 8))
            .shadow(color: AppPalette.shadow, radius: 24, x: 0, y: 14)
            .overlay(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 8)
                    .fill(
                        LinearGradient(
                            colors: [Color.white.opacity(0.70), Color.white.opacity(0.12)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(height: 1)
                    .padding(.horizontal, 12)
            }
    }
}

private extension View {
    func glassCard() -> some View {
        modifier(GlassCardModifier())
    }
}

private struct GlassTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .textFieldStyle(.plain)
            .padding(.horizontal, 11)
            .padding(.vertical, 8)
            .font(AppTypography.korean(size: 14, weight: .medium))
            .foregroundStyle(AppPalette.textPrimary)
            .background(Color.white.opacity(0.66), in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(AppPalette.stroke, lineWidth: 1))
    }
}

private enum GlassButtonKind {
    case primary
    case secondary
}

private struct GlassButtonStyle: ButtonStyle {
    let kind: GlassButtonKind

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AppTypography.korean(size: 13, weight: .semibold))
            .foregroundStyle(kind == .primary ? .white : AppPalette.textPrimary)
            .lineLimit(1)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .frame(maxWidth: kind == .secondary ? .infinity : nil)
            .background(background(isPressed: configuration.isPressed), in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(kind == .primary ? Color.white.opacity(0.35) : AppPalette.stroke, lineWidth: 1))
            .shadow(color: AppPalette.shadow.opacity(configuration.isPressed ? 0.45 : 1.0), radius: configuration.isPressed ? 4 : 12, y: configuration.isPressed ? 2 : 7)
            .scaleEffect(configuration.isPressed ? 0.985 : 1)
            .animation(.easeOut(duration: 0.18), value: configuration.isPressed)
    }

    private func background(isPressed: Bool) -> LinearGradient {
        let opacity = isPressed ? 0.76 : 0.90
        switch kind {
        case .primary:
            return LinearGradient(
                colors: [
                    AppPalette.accentTeal.opacity(opacity),
                    AppPalette.accentPurple.opacity(opacity * 0.88)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .secondary:
            return LinearGradient(
                colors: [
                    Color.white.opacity(isPressed ? 0.48 : 0.66),
                    Color.white.opacity(isPressed ? 0.32 : 0.50)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }
}

enum OutputKind {
    case korean
    case bilingual
}

struct RuntimeSettings {
    let repoPath: String
    let baseURLOverride: String
    let apiKeyOverride: String
}

final class TranslatorModel: ObservableObject {
    @Published var repoPath: String
    @Published var baseURLOverride: String
    @Published var apiKeyOverride = ""
    @Published var clipboardPreview = ""
    @Published var logText = ""
    @Published var statusText = "대기"
    @Published var lastPaperID = ""
    @Published var isRunning = false

    private var currentProcess: Process?
    private let defaults = UserDefaults.standard

    init() {
        let detectedRepo = Self.detectRepoPath() ?? FileManager.default.currentDirectoryPath
        repoPath = defaults.string(forKey: "repoPath") ?? detectedRepo
        baseURLOverride = defaults.string(forKey: "baseURLOverride") ?? ""
    }

    func saveSettings() {
        defaults.set(repoPath, forKey: "repoPath")
        defaults.set(baseURLOverride, forKey: "baseURLOverride")
        appendLog("settings saved")
    }

    func loadClipboardPreview() {
        clipboardPreview = NSPasteboard.general.string(forType: .string)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }

    func translateClipboardURL() {
        let value = NSPasteboard.general.string(forType: .string)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        clipboardPreview = value
        guard let url = URL(string: value), let scheme = url.scheme, scheme.hasPrefix("http") else {
            appendLog("error: clipboard does not contain an HTTP(S) URL")
            return
        }
        let paperID = Self.paperID(from: url)
        let settings = runtimeSettings()
        startWorkflow(paperID: paperID, title: "URL 번역") { [weak self] in
            try await self?.runCommand(["fetch", "--paper-id", paperID, "--source-url", value, "--force", "--json"], settings: settings)
            try Self.validateModelEndpoint(settings: settings)
            try await self?.runCommand(["translate", "--paper-id", paperID, "--json"], settings: settings)
            try await self?.runCommand(["restyle", "--paper-id", paperID, "--json"], settings: settings)
        }
    }

    func handleDrop(providers: [NSItemProvider]) -> Bool {
        guard !isRunning else { return false }
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) }) else {
            appendLog("error: dropped item is not a file")
            return false
        }
        provider.loadDataRepresentation(forTypeIdentifier: UTType.fileURL.identifier) { [weak self] data, error in
            if let error {
                DispatchQueue.main.async {
                    self?.appendLog("error: \(error.localizedDescription)")
                }
                return
            }
            guard
                let data,
                let raw = String(data: data, encoding: .utf8),
                let url = URL(string: raw.trimmingCharacters(in: .whitespacesAndNewlines))
            else {
                DispatchQueue.main.async {
                    self?.appendLog("error: could not read dropped file URL")
                }
                return
            }
            DispatchQueue.main.async {
                self?.translatePDF(url)
            }
        }
        return true
    }

    func translatePDF(_ url: URL) {
        guard url.pathExtension.lowercased() == "pdf" else {
            appendLog("error: only PDF files are supported for drag and drop")
            return
        }
        let paperID = Self.sanitizedID(from: url.deletingPathExtension().lastPathComponent)
        let title = url.deletingPathExtension().lastPathComponent
        let settings = runtimeSettings()
        startWorkflow(paperID: paperID, title: "PDF 번역") { [weak self] in
            try await self?.runCommand(["pdf-import", "--paper-id", paperID, "--pdf", url.path, "--title", title, "--json"], settings: settings)
            try Self.validateModelEndpoint(settings: settings)
            try await self?.runCommand(["translate", "--paper-id", paperID, "--json"], settings: settings)
            try await self?.runCommand(["restyle", "--paper-id", paperID, "--json"], settings: settings)
        }
    }

    func runDoctor() {
        let settings = runtimeSettings()
        startWorkflow(paperID: lastPaperID, title: "doctor") { [weak self] in
            try await self?.runCommand(["doctor", "--json"], settings: settings)
        }
    }

    func cancel() {
        currentProcess?.terminate()
        currentProcess = nil
        setRunning(false, status: "중지됨")
        appendLog("cancel requested")
    }

    func openOutput(kind: OutputKind) {
        guard !lastPaperID.isEmpty else { return }
        let suffix = kind == .korean ? ".ko.paper.html" : ".ko-en.paper.html"
        let url = URL(fileURLWithPath: repoPath)
            .appendingPathComponent("outputs")
            .appendingPathComponent("\(lastPaperID)\(suffix)")
        NSWorkspace.shared.open(url)
    }

    func openOutputsFolder() {
        let url = URL(fileURLWithPath: repoPath).appendingPathComponent("outputs")
        NSWorkspace.shared.open(url)
    }

    private func runtimeSettings() -> RuntimeSettings {
        RuntimeSettings(
            repoPath: repoPath,
            baseURLOverride: baseURLOverride.trimmingCharacters(in: .whitespacesAndNewlines),
            apiKeyOverride: apiKeyOverride.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }

    private func startWorkflow(paperID: String, title: String, operation: @escaping () async throws -> Void) {
        guard !isRunning else { return }
        logText = ""
        lastPaperID = paperID
        setRunning(true, status: "\(title) 실행 중")
        appendLog("paper_id=\(paperID.isEmpty ? "-" : paperID)")
        Task {
            do {
                try await operation()
                DispatchQueue.main.async {
                    self.setRunning(false, status: "완료")
                    self.appendLog("done")
                }
            } catch {
                DispatchQueue.main.async {
                    self.setRunning(false, status: "실패")
                    self.appendLog("error: \(error.localizedDescription)")
                }
            }
        }
    }

    private func runCommand(_ arguments: [String], settings: RuntimeSettings) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                let script = URL(fileURLWithPath: settings.repoPath).appendingPathComponent("scripts/paper_translator.py")
                guard FileManager.default.fileExists(atPath: script.path) else {
                    continuation.resume(throwing: AppError.message("scripts/paper_translator.py not found at \(script.path)"))
                    return
                }
                guard let python = Self.resolvePythonExecutable(repoPath: settings.repoPath) else {
                    continuation.resume(throwing: AppError.message(".venv Python not found. Run scripts/bootstrap_python_env.sh first."))
                    return
                }

                let process = Process()
                process.currentDirectoryURL = URL(fileURLWithPath: settings.repoPath)
                process.executableURL = python
                process.arguments = [script.path] + arguments

                var env = ProcessInfo.processInfo.environment
                env["UV_CACHE_DIR"] = ".uv-cache"
                if !settings.baseURLOverride.isEmpty {
                    env["OPENAI_BASE_URL"] = settings.baseURLOverride
                }
                if !settings.apiKeyOverride.isEmpty {
                    env["OPENAI_API_KEY"] = settings.apiKeyOverride
                }
                process.environment = env

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe
                pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                    let data = handle.availableData
                    guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
                    DispatchQueue.main.async {
                        self?.appendLog(text.trimmingCharacters(in: .newlines))
                    }
                }

                DispatchQueue.main.async {
                    self.currentProcess = process
                    let displayPython = python.path.replacingOccurrences(of: settings.repoPath + "/", with: "")
                    self.appendLog("$ \(displayPython) scripts/paper_translator.py \(arguments.joined(separator: " "))")
                }

                do {
                    try process.run()
                    process.waitUntilExit()
                    pipe.fileHandleForReading.readabilityHandler = nil
                    DispatchQueue.main.async {
                        if self.currentProcess === process {
                            self.currentProcess = nil
                        }
                    }
                    if process.terminationStatus == 0 {
                        continuation.resume()
                    } else {
                        continuation.resume(throwing: AppError.message("command exited with status \(process.terminationStatus)"))
                    }
                } catch {
                    pipe.fileHandleForReading.readabilityHandler = nil
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func setRunning(_ running: Bool, status: String) {
        isRunning = running
        statusText = status
    }

    private func appendLog(_ line: String) {
        guard !line.isEmpty else { return }
        if logText.isEmpty {
            logText = line
        } else {
            logText += "\n" + line
        }
        if logText.count > 120_000 {
            logText.removeFirst(logText.count - 120_000)
        }
    }

    private static func paperID(from url: URL) -> String {
        let raw = url.absoluteString
        if let range = raw.range(of: #"(\d{4}\.\d{4,5})v\d+"#, options: .regularExpression) {
            return "arxiv-" + raw[range].replacingOccurrences(of: #"v\d+$"#, with: "", options: .regularExpression)
                .replacingOccurrences(of: ".", with: "-")
        }
        let seed = [url.host ?? "paper", url.deletingPathExtension().lastPathComponent]
            .filter { !$0.isEmpty }
            .joined(separator: "-")
        return sanitizedID(from: seed)
    }

    private static func sanitizedID(from text: String) -> String {
        let lower = text.lowercased()
        let mapped = lower.map { char -> Character in
            if char.isLetter || char.isNumber {
                return char
            }
            return "-"
        }
        let collapsed = String(mapped).replacingOccurrences(of: #"-+"#, with: "-", options: .regularExpression)
        let trimmed = collapsed.trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return trimmed.isEmpty ? "paper" : trimmed
    }

    private static func detectRepoPath() -> String? {
        let fileManager = FileManager.default
        let starts = [
            URL(fileURLWithPath: fileManager.currentDirectoryPath),
            Bundle.main.bundleURL,
            Bundle.main.resourceURL
        ].compactMap { $0 }

        for start in starts {
            var cursor = start.standardizedFileURL
            for _ in 0..<10 {
                let candidate = cursor.appendingPathComponent("paper-translator")
                if fileManager.isExecutableFile(atPath: candidate.path) {
                    return cursor.path
                }
                let parent = cursor.deletingLastPathComponent()
                if parent.path == cursor.path { break }
                cursor = parent
            }
        }
        return nil
    }

    private static func resolvePythonExecutable(repoPath: String) -> URL? {
        let fileManager = FileManager.default
        let candidates = [
            URL(fileURLWithPath: repoPath).appendingPathComponent(".venv/bin/python"),
            URL(fileURLWithPath: repoPath).appendingPathComponent(".venv/bin/python3")
        ]
        for candidate in candidates where fileManager.isExecutableFile(atPath: candidate.path) {
            return candidate
        }
        return nil
    }

    private static func validateModelEndpoint(settings: RuntimeSettings) throws {
        let baseURL = effectiveBaseURL(settings: settings)
        guard !baseURL.isEmpty else {
            throw AppError.message("Base URL이 비어 있습니다. 설정에 6번 서버 주소를 입력하거나 .env에 OPENAI_BASE_URL을 넣어주세요.")
        }
        guard let url = URL(string: baseURL), let host = url.host else {
            throw AppError.message("Base URL 형식이 올바르지 않습니다: \(baseURL)")
        }
        let port = UInt16(url.port ?? (url.scheme == "https" ? 443 : 80))
        guard canReach(host: host, port: port, timeout: 2.0) else {
            throw AppError.message("Base URL에 연결할 수 없습니다: \(baseURL)\n6번 서버를 쓰려면 설정 또는 .env의 OPENAI_BASE_URL을 http://121.126.210.6:8317/v1 로 맞춰주세요.")
        }
    }

    private static func effectiveBaseURL(settings: RuntimeSettings) -> String {
        if !settings.baseURLOverride.isEmpty {
            return settings.baseURLOverride
        }
        return envValue(repoPath: settings.repoPath, key: "OPENAI_BASE_URL") ?? ""
    }

    private static func envValue(repoPath: String, key: String) -> String? {
        let envURL = URL(fileURLWithPath: repoPath).appendingPathComponent(".env")
        guard let contents = try? String(contentsOf: envURL, encoding: .utf8) else {
            return nil
        }
        for rawLine in contents.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !line.isEmpty, !line.hasPrefix("#") else { continue }
            let parts = line.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
            guard parts.count == 2, parts[0].trimmingCharacters(in: .whitespacesAndNewlines) == key else {
                continue
            }
            return String(parts[1])
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
        }
        return nil
    }

    private static func canReach(host: String, port: UInt16, timeout: TimeInterval) -> Bool {
        guard let nwPort = NWEndpoint.Port(rawValue: port) else {
            return false
        }
        let semaphore = DispatchSemaphore(value: 0)
        let queue = DispatchQueue(label: "paper-translator.endpoint-check")
        let connection = NWConnection(host: NWEndpoint.Host(host), port: nwPort, using: .tcp)
        var isReady = false

        connection.stateUpdateHandler = { state in
            switch state {
            case .ready:
                isReady = true
                semaphore.signal()
            case .failed, .cancelled:
                semaphore.signal()
            default:
                break
            }
        }
        connection.start(queue: queue)
        _ = semaphore.wait(timeout: .now() + timeout)
        connection.cancel()
        return isReady
    }
}

enum AppError: LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self {
        case .message(let value):
            return value
        }
    }
}
