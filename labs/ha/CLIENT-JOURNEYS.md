# Private R08 production client rehearsal

Source preparation only. The coordinator performs actual mutations after T034's
matching fixture gate and the reviewed T035 source/resource packet. No instruction
here creates a public HA deployment path. R01/R05/R06 homes, model, keys, simulator
bundles and retirement schedules are not inputs to this rehearsal.

## Production startup gate

Before approving an operation, retain all of the following actual observations:

1. Freeze the integrated production Python/Node/Dart/Swift sources. The REAL
   source map must include `hud_ingress.mjs`, the production HUD modules, the
   exact `dist/.vite/manifest.json` and its built asset closure, and the installed
   production Node dependency closure needed by Express. Include qualified
   dependency bytes as ordinary files, not links into a mutable checkout.
   `Rehearsal` refuses later additions to its frozen source. Do not copy an old
   built HUD or resolve another npm version after the source gate. A separate
   reviewed build/source packet may be prepared before the gate; freeze its
   current built assets and runtime dependency bytes together. Existing source
   bounds remain 20,000 files/512MiB; a minimal runtime closure is sufficient.
   `hud_closure.mjs` deterministically inventories the actual installed Express
   production dependency graph, all other literal bare modules in the production
   HUD source graph, and only the Vite entry asset closure. It follows installed
   nested package resolution and `dependencies`/present optional dependencies,
   checks actual package versions against the lock, and rejects nonliteral source
   imports, outside resolutions, symlinks and hard links. It does not install npm
   packages, execute dependency scripts, launch a server or include unrelated
   development packages. Use after the coordinator's final HUD build:

   ```text
   node labs/ha/hud_closure.mjs inventory SOURCE_ROOT /PRIVATE/hud-closure.json
   node labs/ha/hud_closure.mjs copy SOURCE_ROOT /PRIVATE/copied-closure.json /PRIVATE/NEW_COPY
   ```

   `inventory` only reads source and writes a new0600 manifest; the optional copy
   uses a new separate directory and ordinary readonly files. Merge the returned
   `source_files` with the main source map, requiring matching hashes for overlaps;
   the REAL runner then copies those exact bytes from the same source root. Never
   append files to an already-frozen tree. Include the helper source itself in
   the main map. Read-only inventory of the currently installed root closure
   found74dependency instances,705files and5,313,668bytes; these are an estimate,
   not the final built source pin. Re-inventory after the final build. Normal
   production module import must succeed from the resulting frozen closure before
   any listener starts; missing/dynamic dependency discovery is a gate failure.

2. Materialize three distinct Border profile2/launch-schema3 homes and one member.
   Use the pinned qualified Python environment; validate every launch contract.
   Start only the exact owned production daemons. Capture private status, current
   leader/epoch, three authenticated iN2N attachments, member catalog/profile
   pins and exact edge listener status. `start-role` returning a PID is not
   readiness; the startup descriptor must exist before the HUD is prepared.
3. The actual daemon must report edge listeners on `127.0.0.1` with each reviewed
   `N2N_EDGE_WS_PORT`, `/mobile/ws` and the matching `NETCLAW_MOBILE_ORIGIN`.
   Cluster role launch sets that origin from its contract. BGP, private API,
   iN2N, quorum and HTTPS ports must remain mutually distinct.
4. Retain model health/confinement, fresh guard capability and native tool source
   readiness. Those checks must not send a speculative model inference or native
   operation. The first inference belongs to an original approved operation.

The new `hud_ingress.mjs` serves the **production** `createProtectedServer`
request handler and pinned Vite assets in three separately owned processes, each
with one TLS listener. There is
no intermediate public HTTP port, synthetic page, mocked operator bridge or
alternate authorization path. Only the exact `/mobile/ws` upgrade is bridged to
the corresponding private edge port, preserving the original Host/Origin. All
other HTTPS requests pass the production route/origin/identity/CSRF checks.
Node/manifest/profile/contract/source/asset/TLS pins are checked before listen;
three HTTPS keys must be distinct. TLS1.3, exact localhost DNS/IP SAN and current
certificate validity are required. No client CA private key is needed by clients.

From the frozen source, with the qualified, hash-recorded Node executable:

```text
node ROOT/source/labs/ha/hud_ingress.mjs prepare ROOT
node ROOT/source/labs/ha/hud_ingress.mjs check ROOT
node ROOT/source/labs/ha/hud_ingress.mjs serve ROOT border0
node ROOT/source/labs/ha/hud_ingress.mjs serve ROOT border1
node ROOT/source/labs/ha/hud_ingress.mjs serve ROOT border2
```

`prepare` creates fresh0700/0600 `ROOT/hud-ingress` configuration and pins;
`check` opens no listener. Launch the three `serve` commands as independently
owned processes with separate logs and PID/start-time records. Each exclusively
claims its selected Border, reads only that Border's private runtime descriptor
and HTTPS key, binds its one reviewed loopback HTTPS port, and records its
PID/origin/installation. It does not
launch Python, Docker, a provider, browser, Code or simulator. It stops its own
listeners after30minutes (override with `NETCLAW_INGRESS_LIFETIME_S`, 60-5400 seconds) or SIGTERM/SIGINT; each listener has32connections,
16KiBheaders,30sHTTP requests,5sWSS handshakes and16MiB total per WSS connection.
The120sWSS idle bound permits ordinary protocol heartbeats. Never remove a serve
claim to repair uncertain startup; preserve it and inspect exact owned sockets.
The per-node `serve-borderN.claim.json`, `listening-borderN.json` and
`stopped-borderN.json` receipts preserve independent ownership. Each listening
receipt deliberately says `execution_ready:false`. All processes run under the
same qualification OS account; this is process-failure isolation, not a claim
that filesystem permissions isolate mutually hostile hosts. A selected Border
front-door fault stops only its exact ingress PID. Observe the other two HTTPS
listeners before and after that fault.

Retain the actual process command/source hash and all three strict-TLS
`/api/runtime` results. Match cluster/generation/manifest, separate installation
and serving-node IDs, open-lab principal and current authority. Check the actual
catalog through every ingress. Refuse redirects or a changed manifest/identity.
Do not interpret TCP/HTTPS reachability as admission authority.

Browser trust must be restricted to the coordinator's fresh profile/process and
reviewed local CA/key set; `ignoreHTTPSErrors` stays false. Code gets the reviewed
CA only in its owned process environment (`NODE_EXTRA_CA_CERTS`) with the
existing isolated fetch settings. The fresh simulator alone receives the public
CA. Do not alter host Keychains/roots or an existing browser/editor/simulator.
Check exact configured origins in each client's normal TLS stack before approval.

## Three original operations, then status-only recovery

Three positives are sufficient **if** the fault schedule maps them to all three
actual ingress nodes and the required majority/new-operation witnesses. Assign
surfaces to node IDs after observing the initial leader; do not assume Border0
won election. Reserve all three in the same durable budget, one at a time.

| Original native sender | Required positive witness |
|---|---|
| Browser HUD | Prepare and approve once through one healthy Border, preferably the initial leader; save its original signed result/ACK before faulting that leader |
| Mac Code1.109 | A distinct native exact review/approval through another Border after actual leader death and successor election; this supplies the distinct post-loss operation |
| Native iOS | Actual QR enrollment, native prepare and one exact approval through the remaining Border; schedule this as the required majority-positive asymmetric-partition witness if the reviewed fault matrix permits |

Each consumes at most2inferences/1nativeeffect from the shared10/20/10 budget,
180soperation/60sinference. The expected positive subtotal is3/6/3, not permission
to fill the remaining budget. Stop on an unknown or failed positive; preserve its
claim, IDs and evidence. Never allocate a replacement ID to repair the client.
Additional positive work is justified only by an unmapped explicit matrix row.
Negative/control rows and result recovery should add no execution.

Browser/Code `original_once` waits for coordinator reservation/claim_send after
its actual native prepare. Mobile has separate `prepare` and `approve` phases;
its exact exported review must receive the same reservation/claim_send and
`surface:mobile` claim before the native checkbox/approval. No frontend budgets
or copied approvals. Export the actual result, successor ACK, member durable ACK,
original review/principal and referenced GAIT commits before settling the slot.
Do not present the open-lab HUD/Code principal's operation as the device principal's
own result. Mobile owns its separate original operation and device proof.

After each positive, run original-result and cold recovery. Keep the same original
browser tab/profile for sessionStorage evidence (the browser's `cold_recovery`
name does not guarantee storage survives a new process). Code must exit/relaunch
with its original profile ID/reference, then exercise native endpoint replacement
against another enrolled node. Mobile must retain the same bundle, Keychain key,
subject, enrollment generation, cluster audience and operation reference through
`select-node`, actual OS background/resume and cold termination/relaunch. No
re-enrollment, storage seeding or copied sessionStorage is recovery evidence.

All three surfaces must separately witness an authority change and no quorum
under SC-004. Keep native Mobile authenticated and waiting at its ready marker
before removing quorum; a new hello correctly refuses when current revocation
state cannot be checked. Use `cluster_recovery_test.dart`'s existing ready/fault
markers and exact original reference. It never prepares/approves/reconciles.
A no-quorum retained view must show a warning and disabled new work; no fresh
status is fabricated. After quorum returns, read the same signed record.

Stale-review proof must start from an actual pending `attempt_count:0` review,
then change authority while preserving that reference. Merely displaying a
completed operation with disabled approval does not prove stale-review refusal.
Browser/Code support `prepare_review` without any approved effect; these controls
may use dedicated pending-only profiles. Mobile's existing `stale-review` phase
requires its retained pending operation. Arrange that record through production
UI without discarding the completed original-reference history. If the current
UI cannot retain both, record that workflow gap and fix it before claiming T040.
These pending prepares do not consume an approved-operation budget slot.

For every recovery/fault phase, independently capture actual cumulative model
and native effect counters **before and after**. Browser/editor's helper hashes
one configured counter file; that file must be refreshed from actual counters
or paired with independent fresh exports. An unchanged stale file is insufficient.
Preserve all failed phases, wire attempts, frontend sent markers and exact source
pins. No fault row is closed merely because a client button is disabled.

## Fresh iOS harness build recipe (coordinator only)

This follows the verified R07 approach while using only current R08 source. The
read-only R07 provenance/recipe is background evidence, never an app/key/config
input. Local Ruby `xcodeproj`1.28.1 is available. Use the already-qualified
Flutter3.44.8/Dart3.12.2 and Xcode27.2 toolchain. No commands below were executed
as part of this source preparation.

Set `R08_SOURCE` to the frozen source, and `R08_NATIVE` to a new private directory
outside that immutable source. Record these literal paths and the toolchain
hashes in the coordinator packet. The new app has its own bundle and software
Keychain tag. Do not copy `GoogleService-Info.plist`, the production iOS project,
a Watch project, an existing simulator home, or any owner enrollment data.

```sh
umask 077
R08_MOBILE="$R08_SOURCE/mobile/netclaw-mobile"
R08_APP="$R08_NATIVE/app"
flutter create --platforms=ios --no-pub --org ca.automateyournetwork.qualification \
  --project-name netclaw_r08_qualification "$R08_APP"
```

Write the fresh harness `pubspec.yaml` with the exact path above (YAML-quoted):

```yaml
name: netclaw_r08_qualification
publish_to: none
version: 1.0.0+1
environment:
  sdk: ^3.12.2
dependencies:
  flutter:
    sdk: flutter
  netclaw_mobile:
    path: /ABSOLUTE/R08_SOURCE/mobile/netclaw-mobile
dev_dependencies:
  flutter_test:
    sdk: flutter
  integration_test:
    sdk: flutter
flutter:
  uses-material-design: true
  assets:
    - assets/illustrations/
    - assets/icon/
```

Copy only the frozen production `assets/illustrations` and `assets/icon`, the
current `pubspec.lock` as the initial lock, `integration_test/mobile_qr_test.dart`,
`integration_test/cluster_recovery_test.dart`, and the two same-named
`test_driver/*_driver.dart` into the new corresponding harness directories.
Relative imports between the two tests remain intact. Copy
`integration_test/native/R08SimulatorPlugin.swift`,
`ios/Runner/X509SelfSigned.swift` and `ios/Runner/ClusterPublicCrypto.swift` into
the fresh `ios/Runner/`. Record each source/destination hash. The simulator plugin
contains the distinct `ca.automateyournetwork.r08.qualification.key` namespace
and no private-key-export method. Never register it in the production app.

Replace only the fresh harness AppDelegate with:

```swift
import Flutter
import UIKit
@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(_ application: UIApplication,
    didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: options)
  }
  func didInitializeImplicitFlutterEngine(_ bridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: bridge.pluginRegistry)
    if let registrar = bridge.pluginRegistry.registrar(forPlugin: "R08SimulatorPlugin") {
      R08SimulatorPlugin.register(with: registrar)
    }
  }
}
```

Add the three Swift files to the actual Runner target using the installed parser,
and bind only this new project to the separate qualification bundle:

```sh
ruby -rxcodeproj - "$R08_APP/ios/Runner.xcodeproj" <<'RUBY'
project = Xcodeproj::Project.open(ARGV.fetch(0))
target = project.targets.find { |t| t.name == 'Runner' } or abort 'Runner missing'
group = project.main_group.find_subpath('Runner') or abort 'Runner group missing'
%w[R08SimulatorPlugin.swift X509SelfSigned.swift ClusterPublicCrypto.swift].each do |name|
  abort 'duplicate source' if group.files.any? { |f| f.path == name }
  target.add_file_references([group.new_file(name)])
end
project.build_configurations.each { |c| c.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '16.2' }
project.targets.each do |t|
  t.build_configurations.each do |c|
    c.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '16.2'
    c.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = 'ca.automateyournetwork.qualification.netclawR08Qualification' + (t.name == 'Runner' ? '' : '.RunnerTests')
  end
end
project.save
RUBY
```

From the new app directory, `flutter pub get --offline` resolves the copied lock
against already available packages. Retain the final lock/hash and actual plugin
versions; an unavailable package is a preparation failure, not permission to
change the reviewed closure silently. The test entrypoint invokes production
`EnrollmentGate` and owner/device screens directly; it does not call production
`main()` or initialize the unrelated Firebase/watch workflow. Preserve normal TLS
validation and generated plugin registration.

Build both target artifacts, retaining each before the next build:

```sh
flutter build ios --simulator --debug --no-pub --target=integration_test/mobile_qr_test.dart
# Copy the resulting Runner.app to a NEW private binaries/qr/Runner.app.
flutter build ios --simulator --debug --no-pub --target=integration_test/cluster_recovery_test.dart
# Copy the resulting Runner.app to a NEW private binaries/recovery/Runner.app.
```

Record Runner and Dart kernel hashes, resolved bundle ID, source pins and build
logs for both binaries. A successful build is not T040 acceptance. The coordinator
later creates one fresh iPhone17Pro/iOS26.5 simulator, records its exact UDID and
initial Shutdown state, and trusts only `ROOT/https-pki/https-ca.crt` within that
owned simulator (`simctl keychain UDID add-root-cert`). No system root changes.

Actual phase invocation uses the matching pinned binary and driver:

```sh
flutter drive --no-pub --keep-app-running \
  --use-application-binary=/PRIVATE/PINNED/Runner.app \
  --driver=test_driver/mobile_qr_driver.dart \
  --target=integration_test/mobile_qr_test.dart -d OWNED_UDID
```

For recovery, substitute the recovery binary and cluster recovery target/driver.
Set `NETCLAW_NATIVE_REPORT` to an absent0600 destination in the private evidence
root. Atomically deliver only the bounded private Documents config after launch.
Resolve `simctl get_app_container UDID BUNDLE data` again after every install or
launch; Flutter may change the container path. Export old private reports/markers
before the next phase; never copy a previous enrollment into a replacement app.
Cold-recovery claims require real termination/relaunch receipts, and background
claims require actual OS paused/resumed evidence, not injected widget events.
The drivers have bounded waits; a failed phase remains recorded and unsent/unknown.

## Requirements still needing actual evidence

T035–T040 require the frozen runtime packet, actual three-ingress positive records,
all required REAL control/fault rows, independently refreshed counters, native
trust/failover/refusal/lifecycle receipts and original signed-result correlation.
T041 additionally requires separate detection/election/recovery measurements,
300ms RTT and storage/clock/resource bounds. This ingress source and build recipe
close none of those evidence gates on their own. T046 cleanup must export first,
then stop only exact owned listeners/PIDs/simulator and remove scoped trust with
that owned simulator; recheck retained runtimes and retirement receipts. Preserve
unknown ledgers, claims and artifacts. R09, physical camera/iPhone/Secure Enclave,
Android, Windows/WSL and actual geographic continuity remain unqualified.
