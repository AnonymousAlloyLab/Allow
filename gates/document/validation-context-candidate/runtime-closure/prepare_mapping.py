"""Prepare a conservative frozen case audit. Does not execute tests, SQL or final binder."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def save(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')

records={}
def py(class_name,name,assertions):
    path=ROOT/'retrieval/tests/test_validation_context.py'
    tree=ast.parse(path.read_text())
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef)and node.name==class_name)
    method=next(node for node in cls.body if isinstance(node,ast.FunctionDef)and node.name==name)
    body='\n'.join(path.read_text().splitlines()[method.lineno-1:method.end_lineno])+'\n'
    identifier='python:'+class_name+'.'+name
    records[identifier]={'kind':'python_test','source':str(path.relative_to(ROOT)),'source_sha256':sha(path),
      'symbol':'test_validation_context.'+class_name+'.'+name,'line':method.lineno,'end_line':method.end_lineno,
      'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'assertions_reviewed':assertions,
      'result_report':'gates/document/inherited-runtime-tests.json','raw_log':'gates/document/inherited-runtime-tests.log'}
    return identifier

def java(class_name,name,assertions):
    path=ROOT/'backend/src/test/java'/Path(class_name.replace('.','/')+'.java')
    identifier='java:'+class_name+'#'+name
    require=bool(re.search(r'\bvoid\s+'+re.escape(name)+r'\s*\(',path.read_text()))
    assert require,(class_name,name)
    records[identifier]={'kind':'junit_test','source':str(path.relative_to(ROOT)),'source_sha256':sha(path),
      'class':class_name,'method':name,'assertions_reviewed':assertions,
      'result_xml':'backend/target/surefire-reports/TEST-'+class_name+'.xml',
      'build_manifest':str((CANDIDATE/'final-build/build-manifest.json').relative_to(ROOT))}
    return identifier

def artifact(identifier,path,assertions):
    records[identifier]={'kind':'registered_report','path':path,'sha256':sha(ROOT/path),'assertions_reviewed':assertions}
    return identifier

P={}
for cls,name,assertions in [
('ValidationContextWireTests','test_context_arguments_reject_before_connection',['Reject revision None/True/negative/>safe/string/float; invalid IDs/container/duplicate/unsorted and missing/extra arg keys; connect mock never called.']),
('ValidationContextWireTests','test_context_accepts_safe_integer_and_id_count_boundaries',['4096 canonical IDs accepted and safe max revision preserved.']),
('ValidationContextWireTests','test_closed_cli_shape_and_strict_json',['Duplicate top-level JSON, invalid UTF8, NaN/unsafe number, Boolean protocol,extra field, malformed/noncanonical nonce, trailing frame,wrong op and forged scope reject before Store.']),
('ValidationContextWireTests','test_cli_dispatch_has_one_context_call',['Empty-ID request dispatches exactly one validation_context; legacy read/owned_ids never called.']),
('ValidationContextWireTests','test_full_cli_output_boundary_and_nonce',['Whole OK envelope exactly1572864bytes plus newline succeeds; one extra byte returns bounded UNAVAILABLE with no artifact.']),
('ValidationContextWireTests','test_read_failure_never_invents_mutation_uncertainty',['Injected _read ValueError/KeyError/OperationalError/UncertainCommit/KnownRollback produce UNAVAILABLE without artifact.']),
('ValidationContextWireTests','test_transaction_exit_failure_discards_complete_context',['Injected failure after yielding snapshot data prevents publication; UNAVAILABLE without artifact.']),
('ValidationContextWireTests','test_legacy_mutation_uncertainty_remains',['Existing finalize UncertainCommit and KnownRollback remain their distinct statuses.']),
('ValidationContextSQLTests','test_actual_snapshot_mode_read_only_and_legacy_mode',['Real transaction reports repeatable read/on; UPDATE denied; legacy transaction reports read committed/off.']),
('ValidationContextSQLTests','test_actual_cli_context_and_database_error_envelopes',['Actual context success echoes nonce/document; real SELECT1/0 history error produces UNAVAILABLE, no artifact, head0 remains.']),
('ValidationContextSQLTests','test_proxy_connection_failure_has_no_fallback',['Injected canonical connect failure called exactly once, no retry/fallback.']),
('ValidationContextSQLTests','test_context_matches_legacy_at_quiescence_and_exact_source',['At head1, base0 and1 whole closed context equals separate legacy read/owned_ids; exact CRLF source preserved.']),
('ValidationContextSQLTests','test_empty_ids_authorize_base_and_skip_scan',['Empty IDs return empty inventory and missingdoc/futurebase still fail; collect_ids spy rejects any invocation.']),
('ValidationContextSQLTests','test_missing_and_foreign_context_never_reaches_inventory',['Foreign principal/workspace and absentbase fail; inventory seam cannot run.']),
('ValidationContextSQLTests','test_logical_launch_does_not_partition_document_history',['Another actual initialized logicalLaunch under same owner/workspace gets same context.']),
('ValidationContextSQLTests','test_requested_kind_inventory_and_text_only',['All8kinds projected, repeated histories collapse; targetId-only references/unknown/unrequested absent; module=null contributes no IDs.']),
('ValidationContextSQLTests','test_complete_history_collision_and_malformed_artifact_fail',['Requested signature/field collision fails even afterfirstmatch; unrequestedconflict empty; malformed laterJSON fails.']),
('ValidationContextSQLTests','test_reads_do_not_mutate_and_full_quota_remains_readable',['Exact workspace/artifact/revision/receipt/admission/head beforeafter valid/repeat/missing; all logical quota counters set to max and read succeeds.']),
('ValidationContextSQLTests','test_commit_after_snapshot_is_excluded_from_head_and_inventory',['Barrier after complete _validation_snapshot setup; concurrent append excluded fromhead0/map{},newrequest seeshead1/newsignature, immutablebase equal.']),
('ValidationContextSQLTests','test_commit_between_base_and_inventory_cannot_mix_snapshots',['Barrier after _read; concurrent signature excluded oldinventory and included newrequest; immutablebase equal.']),
('ValidationContextSQLTests','test_future_base_committed_after_snapshot_requires_new_request',['Futurebase1 absent in oldsnapshot even aftercommit; separate request seesbase1/newsignature.']),
('ValidationContextSQLTests','test_connection_closes_before_context_is_returned',['Actual canonical connection count1 and closed at successful Store return.'])]:
 P[name]=py(cls,name,assertions)
J={}
for cls,name,assertions in [
('DocumentValidationContextTest','missingModuleStillReadsOneContext',['MissingNode module causes one validationContext request,exactclosed args,empty IDs,no more gateway interactions.']),
('DocumentValidationContextTest','sortsAndDeduplicatesAllServerPrefixedValues',['Nested values collected,saved requested set sorted and deduplicated.']),
('DocumentValidationContextTest','retainsExactSourceAndDefensiveCopies',['CRLF/nonBMP source retained and returned nodes cannot mutate storedcontext.']),
('DocumentValidationContextTest','permitsAllEightHistoricalKinds',['All8knownkindstrings accepted only under requestedID.']),
('DocumentValidationContextTest','doesNotInventMissingOwnership',['Requested ID missing from inventory stays missing.']),
('DocumentValidationContextTest','rejectsMalformedArgumentsBeforeBridge',['Negative/unsafe revision and malformeddocument/serverID start no gateway.']),
('DocumentValidationContextTest','enforcesDistinctIdCountBeforeBridge',['4096 distinct IDs call gateway;4097 denied before gateway.']),
('DocumentValidationContextTest','rejectsMismatchedIdentityAndRevisions',['Wrongdocument/base,negative/unsafe/float/string observedhead and wrong scalar identity reject. Positivehead<base is not isolated.']),
('DocumentValidationContextTest','rejectsMalformedShapes',['Missinghead,extra contextkey,nullartifact,extra artifactkey and missing sourceHash reject.']),
('DocumentValidationContextTest','rejectsForeignOrMalformedInventory',['Unrequestedkey,unknown/nontextkind,arrayinventory reject.']),
('DocumentValidationContextTest','rejectsOversizedBaseArtifact',['Artifact with1MiB source plus metadata exceedsartifactcap and rejects.']),
('DocumentValidationContextTest','permitsObservedHeadBeyondExactBase',['Observedhead9 accepted forbase0 withoutchangingreturnedartifact.']),
('DocumentValidationContextTest','failedContextPreventsWorkerConstruction',['NonOK context causes no DocumentWorker construction; lease can be acquired afterward.']),
('DocumentValidationContextTest','interruptedContextPreventsWorkerConstruction',['Interrupted gateway causes no DocumentWorker construction; lease released.']),
('DocumentContextTransportTest','rejectsWrongNonceFromExitedBridge',['Actual exitedtestbridge wrongnonce rejected.']),
('DocumentContextTransportTest','rejectsWrongProtocolFromExitedBridge',['Actual exitedtestbridge wrongprotocol rejected.']),
('DocumentContextTransportTest','rejectsExtraTransportFields',['Actual extra privateenvelopefield rejected.']),
('DocumentContextTransportTest','classifiesExtraEnvelopeAsUnavailableContext',['Malformedactualprivatebridgeenvelope becomes contextIOException.']),
('DocumentBoundaryTest','exchangesAndReapsFrame',['Actual cat child returns frame only afterexit/reap.']),
('DocumentBoundaryTest','deadlineIncludesBlockedInputAndReaping',['Actualsleepchild blocked stdin deadline rejects and childdead. This is not a2MiBserialized-worker-boundary test.']),
('DocumentWorkerLifecycleTest','reapsBeforeReturningUnidentifiedChildProof',['Actualownedchild missingincarnation is killed/reaped; truthfulprooffields.']),
('DocumentWorkerLifecycleTest','interruptedIdentityFailureStillReaps',['Interrupted caller stillreaps actualownedchild.']),
('BuildIdentityTest','registryBytesAffectIdentity',['Registrybytes mutationchanges fullbuildidentity syntheticfixture.']),
('BuildIdentityTest','resourcePresenceAffectsIdentity',['Adding/deletingresource changes/restores identity syntheticfixture.'])]:
 full='dev.allow.backend.'+cls;J[name]=java(full,name,assertions)

A={
 'integration':artifact('report:current-integration','gates/document/validation-context-candidate/runtime-runs/current-v1/binding-v1/report.json',['Current186Python(including22new+22legacy),SQL52,clientinventory+recovery,309modelprojection,229buildinputs andsamePID826907gen1 allPASS.']),
 'build':artifact('report:full-build','gates/document/validation-context-candidate/final-build/build-manifest.json',['Actual189Java/164frontend,0styleviolations,989documentedboundedcallables, fullcurrentbuildlog/sourcebinding.']),
 'formal':artifact('report:309-model','gates/document/validation-context-candidate/formal-runs/final-309-v1/report.json',['309exactmodelpropositions,2cleanbuilds/axioms/artifacts/provenance; implementationcorrespondence excluded.']),
 'http':artifact('report:http','gates/document/http-smoke.json',['8actualHTTPchecks includeSOURCE/BLOCK exactsource/maps/advisoryrequestHash,typedrejection,acceptedsolverdescriptors anddurablereceipts/history.']),
 'restart':artifact('report:restart','gates/document/restart-report.json',['6actualcrash/restartchecks acceptedhead/artifact/receiptbytes andprivateidentity retained,newbearer.']),
 'doc_recovery':artifact('report:document-recovery','gates/document/document-recovery-report.json',['ActualfullACL/RLS/row/ownerrecovery+freshprocessreceiptreplay,no liveDBtarget.']),
 'browser':artifact('report:browser','gates/document/browser-benchmark-runs/validation-context-v1/report.json',['Registeredactualbrowser100warm+1000samples,p9512.5<50,actualinputs/staticrestorebound;cold/manualAXnotconducted/claimed.']),
 'resource':artifact('report:VC19','gates/document/validation-context-candidate/runtime-profiles/vc19-r1/runs/run-20261103T221837Z/report.json',['9actualseparateboundedCLI samples,64/512/2048/4096rows,max268434782accountedbytes; clientbuffering/kernelRSS/VmPeak/AS/CPU/wall/closedconn/source/proxy/cleanupmeasured. Storage-shaped fixture,notsemanticallyacceptedhistory orstreaming/universalRSSguarantee.'])}

rows=[]
def row(i,refs,covered,gaps=(),notes=()):
 plan=next(item for item in json.loads((CANDIDATE/'runtime-test-plan.json').read_text())['tests']if item['id']==i)
 rows.append({'id':i,'name':plan['name'],'frozen_pass_condition':plan['pass_condition'],'evidence_refs':refs,
   'covered_cases':covered,'remaining_required_cases':[{'gap_id':i+'-G'+str(index+1),'case':gap}for index,gap in enumerate(gaps)],
   'audit_status':'PARTIAL'if gaps else'SUPPORTED_FINITE_EVIDENCE','scope_notes':list(notes)})
row('VC01',[P['test_context_arguments_reject_before_connection'],P['test_closed_cli_shape_and_strict_json'],J['rejectsMalformedArgumentsBeforeBridge']],
 ['Closedarg/nonce/scalar/invalidUTF8/duplicateJSON negativecases demonstrated beforeStore/connect.'],
 ['Completeprivateframe/encodedargs/depth boundary matrix not executed for this new operation; outer missingfields/wrong argscontainer variants not all enumerated.'])
row('VC02',[P['test_actual_snapshot_mode_read_only_and_legacy_mode']],['ActualRepeatableRead/ReadOnly observations andwrite rejection;legacyRC.'],
 ['Actualproxy-only orderedBEGIN/SET/three_scope_SELECT/data/COMMIT trace missing. Observedmode alone doesnot establishfirststatementorder.'])
row('VC03',[P['test_cli_dispatch_has_one_context_call'],P['test_empty_ids_authorize_base_and_skip_scan'],P['test_proxy_connection_failure_has_no_fallback'],J['missingModuleStillReadsOneContext'],A['http']],
 ['Source/missingmodule mandatorysinglecontext,emptyIDs authorizebase andno collect_ids invocation;connectfailure propagates.'],
 ['Empty-ID exactzero_history_SQLscan trace is not recorded (collect_ids spy is narrower).'])
row('VC04',[P['test_context_matches_legacy_at_quiescence_and_exact_source'],J['retainsExactSourceAndDefensiveCopies'],A['http']],
 ['Base0and1/head1 wholeartifact equality tolegacy,exactCRLF/nonBMPsource,maps/metadata comparedas decodedartifact.'])
row('VC05',[P['test_missing_and_foreign_context_never_reaches_inventory'],P['test_empty_ids_authorize_base_and_skip_scan'],P['test_logical_launch_does_not_partition_document_history'],J['failedContextPreventsWorkerConstruction'],J['rejectsMismatchedIdentityAndRevisions']],
 ['Missingdocument/base/foreignprincipal/workspace deny beforeinventory; foreignrequestusesexistingother-scopeUUID; launchdoesnotpartition; genericfailedcontextpreventsworker;returnedforeignDocId rejected.'],notes=['Case composition is finite source/test evidence,not universalRLSorJavarefinement.'])
row('VC06',[P['test_commit_after_snapshot_is_excluded_from_head_and_inventory']],['Realconcurrentcommitafterallscopesetup excluded consistently;newrequest seesboth.'],
 ['RequiredbarrierimmediatelyafterFIRSTscopeSELECT (beforeothertwo) wasnotexecuted.'])
row('VC07',[P['test_commit_between_base_and_inventory_cannot_mix_snapshots'],P['test_future_base_committed_after_snapshot_requires_new_request']],
 ['Realbarrierafterbase read excludesconcurrentID;futurebaseinsideoldsnapshotfails,separatecallsucceeds.'])
row('VC08',[P['test_context_matches_legacy_at_quiescence_and_exact_source'],P['test_commit_after_snapshot_is_excluded_from_head_and_inventory']],
 ['Commitbeforecontextvisibleinhead/inventoryevenforbase0;concurrentappendleaveshistoricalartifactequal.'])
row('VC09',[P['test_requested_kind_inventory_and_text_only'],J['permitsAllEightHistoricalKinds']],
 ['All8kinds,duplicatehistories,requestedonly,reference-onlyabsent,TEXT_ONLYnullmodule.'])
row('VC10',[P['test_complete_history_collision_and_malformed_artifact_fail']],
 ['Laterrequestedkindcollision fails;unrequestedcollisiondoesnotgrantauthority;latermalformedartifactfailscompleteoperation.'])
row('VC11',[J[x]for x in['rejectsMismatchedIdentityAndRevisions','rejectsMalformedShapes','rejectsForeignOrMalformedInventory','rejectsWrongNonceFromExitedBridge','rejectsWrongProtocolFromExitedBridge','rejectsExtraTransportFields','failedContextPreventsWorkerConstruction']],
 ['Foreignidentity/unsafehead/closedshape/kind/nonce/protocol failures exercised atproperprivateboundaries.'],
 ['PositiveheadObserved<matchingbaseRevision is not isolated; existingnegativeheadfails safeinteger guard first.'])
row('VC12',[P['test_full_cli_output_boundary_and_nonce'],J['rejectsOversizedBaseArtifact'],J['deadlineIncludesBlockedInputAndReaping']],
 ['WholeCLI1572864/1572865plusnewline boundary andoversizedartifact rejection;inheritedblockedinputdeadline reaps.'],
 ['At/aroundactualserialized2MiBprivateworker framingguard notexecuted;blocked2MiBstdin fixture isdifferent. Needstructural/adversarialcase withstrongerpublic/artifactbounds disclosed.'])
row('VC13',[P['test_context_accepts_safe_integer_and_id_count_boundaries'],P['test_context_arguments_reject_before_connection'],J['enforcesDistinctIdCountBeforeBridge'],J['sortsAndDeduplicatesAllServerPrefixedValues'],A['http']],
 ['4096accepted/4097denied,sorted/dedupcanonicalservervalues,unsafeIDs/revisions reject,actualpublic262145body400 inheritedHTTP.'],
 ['Private256KiBencodedargs+revision bound lacks exactnegativeguardfixture/invariant; valid4096canonicalUUIDshape cannotreach256KiB,so disclose dominance ratherthan manufacturevalidboundary.'])
row('VC14',[P[x]for x in['test_read_failure_never_invents_mutation_uncertainty','test_transaction_exit_failure_discards_complete_context','test_actual_cli_context_and_database_error_envelopes','test_proxy_connection_failure_has_no_fallback','test_legacy_mutation_uncertainty_remains']]+[J['interruptedContextPreventsWorkerConstruction'],A['integration']],
 ['Injectedread/connection/txexit/decoder-shapederrorsandrealSQLdivisionzero no partialcontext,no mutationuncertainty;interruptedparentnoworker.'],
 ['Context-specific parserdenial/unavailability/auth/brokenproxy/fault-stage matrix incomplete. Inherited52proxynegatives cannotalone establisheverynewcontext stage. Actualvsinjectedfaults mustremainlabelled.'])
row('VC15',[P['test_connection_closes_before_context_is_returned'],P['test_transaction_exit_failure_discards_complete_context'],J['exchangesAndReapsFrame'],J['deadlineIncludesBlockedInputAndReaping'],J['interruptedContextPreventsWorkerConstruction'],J['interruptedIdentityFailureStillReaps']],
 ['ActualStoreconnectionclosedatreturn;genericbridgeexit/reap;failures/interruptionspreventsworkerandreleaselease.'],
 ['Joined successful contextSQLcommit/connectionclose/bridgeexit->actualworkerlaunch ordering trace missing. Genericseparatechecksnotjoinedobservation.'])
row('VC16',[J['registryBytesAffectIdentity'],J['resourcePresenceAffectsIdentity'],J['reapsBeforeReturningUnidentifiedChildProof'],A['http']],
 ['Buildidentitypresence/bytes fences andownedchildreaping; actualHTTPfreshwholevalidationworks; newDocumentWorker construction visibleinsource.'],
 ['TwoactualadvisoryvalidatorPIDinstances withsameflags/resources/fullidentity+changed-build denial notdirectlyrecorded. Source new alone isnotPIDmeasurement.'])
row('VC17',[A['build'],A['http'],A['browser']],
 ['189Java(including55module/type/source/mapcases andsemantic/differentialfixtures),164frontend,actualSOURCE/BLOCKHTTP exactsource/nominal/schema/diagnostics preserved.'],
 ['Explicitforeign/missing/wrong-kind ownedSERVER-ID triplet throughactualfreshworker notlocated incurrentboundtests; privateinventoryshape tests aredifferentlayer.'])
row('VC18',[P['test_reads_do_not_mutate_and_full_quota_remains_readable'],P['test_actual_snapshot_mode_read_only_and_legacy_mode'],P['test_commit_after_snapshot_is_excluded_from_head_and_inventory']],
 ['Exactdurablebeforeaftervalid/repeat/missingcasesandquota-fullread;legitimateappend visibleonlytonewrequest.'],
 ['Exactdurablestate before/aftercontexttimeoutandcancellation absent;readonlysetting isnot a replacement forrequestedcomparisons.'])
row('VC19',[P['test_reads_do_not_mutate_and_full_quota_remains_readable'],A['resource']],
 ['Logicalexactquota exhaustionreadable;actualstorage-shaped4096rows/near256MiBprofile9successsampleswithbufferedrows/rawbytes,RSS/AS/CPU/wall/closedconn andownedDBcleanup.'],
 notes=['No semanticallyaccepted4096-edit-historyreachabilityclaim. Instrumentation/mock addsdisclosedoverhead. libpqclientbuffered notstreaming. No universalheapbound/resource-exhaustionavailabilityguarantee.'])
row('VC20',[A['http'],A['build'],A['browser']],
 ['ActualHTTPrequestHash/draftEpoch retained,frontendstate.test rejectsbody/hash/base/epochstale replies andadvisoryIntegration preservesacceptedreference;privateobservedheadneverpublicstate.'],
 notes=['Frontendpassrecordisfull164suite+frozenassertionsource,not individualcase durations.'])
row('VC21',[A[x]for x in['integration','http','restart','doc_recovery']],
 ['Legacy22docSQL plusfull186/52,actualHTTP8,crashrestart6,receipts/cas/nonces/fullACLrecovery andacceptedsolverdescriptorchecks pass.'])
row('VC22',[A['integration'],P['test_actual_cli_context_and_database_error_envelopes'],P['test_actual_snapshot_mode_read_only_and_legacy_mode']],
 ['Canonicalconnectionhelpersole rawdriver,currentSQL52/clientinventory/proxyidentityandactualcontextqueriesPASS;noallowlistchange.'],
 ['NewcontextBEGIN/mode/scope/read/history/COMMIT orderedtrace/counter+endpointrole binding missing; legacy7entrypointmanifest doesnotexplicitlyregistercompletecontextpath.'])
row('VC23',[A['build']],['Full189Java/164frontend build,96files989callables0styleviolations;checker73JS/TS+13Javafixtures;boundsourceunchanged.'])
row('VC24',[],['Originalfrozen500node/100warm/1000measuredbenchmark running;producer/fixtureknown.'],
 ['Finalrawcandidate1100run+allfailure/statistic/current-source/checkpointcomparison notyetavailable.'],
 notes=['Measurementcompletionandstrictp95<300productacceptance separate;neverforcePASSiforiginaltargetmissed.'])
row('VC25',[A['formal'],A['integration']],['Registered309exactmodeltypes,287inherited+22new,allowedaxioms,nonvacuouswitness,2cleanbuilds/determinism,activeformalprojection.'],notes=['Notimplementationrefinement.'])
row('VC26',[A['browser']],['Newbuildidentityhasfreshregisteredbrowservalidation-context-v1 record,p9512.5<50 with100warm+1000measured,source/staticrestorebound.'],notes=['Coldseries/manualaccessibilityandbroadercommercialgatesexplicitlynotconducted/claimed.'])

assert len(rows)==26 and {row['id']for row in rows}=={'VC'+str(i).zfill(2)for i in range(1,27)}
save('case-mapping-r1.json',{'scope':'Conservative assertion-level audit; gaps block26closure. Mapping is not formal implementation correspondence.','frozen_plan_sha256':sha(CANDIDATE/'runtime-test-plan.json'),'records':records,'obligations':rows})
gaps=[dict(obligation=row['id'],**gap)for row in rows for gap in row['remaining_required_cases']]
save('gap-audit-r1.json',{'status':'BLOCKED','phase':'PRE_FINAL_BINDER_AUDIT_NOT_NEW_TEST_EXECUTION','total_obligations':26,'supported_finite_evidence':sum(not row['remaining_required_cases']for row in rows),'partial_or_pending':sum(bool(row['remaining_required_cases'])for row in rows),'gaps':gaps,'benchmark':'PENDING; independentstrict300msproducttargetunchanged','no_active_changes':True,'next':'Separatelyregisteredgate-localPython/Java probes AFTER currentbenchmark; retain186/189main-suitecounts unchanged.'})
print(json.dumps({'prepared':26,'supported':sum(not row['remaining_required_cases']for row in rows),'partial_or_pending':sum(bool(row['remaining_required_cases'])for row in rows),'gaps':len(gaps)}))
