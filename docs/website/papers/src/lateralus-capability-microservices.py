#!/usr/bin/env python3
"""
Render Capability-Based Microservices in Lateralus: Composing secure, pipeline-driven network services with capability-aware stage boundaries in the canonical Lateralus paper style (A4, Helvetica/Courier).
"""
from pathlib import Path

from _lateralus_template import render_paper

OUT = Path(__file__).resolve().parents[1] / 'pdf' / 'lateralus-capability-microservices.pdf'

TITLE = 'Capability-Based Microservices in Lateralus'
SUBTITLE = 'Composing secure, pipeline-driven network services with capability-aware stage boundaries'
META = 'bad-antics · April 2026 · Lateralus Language Research'

ABSTRACT = """Capability-based security is a strong fit for microservices, especially when service interactions are structured as pipelines. Lateralus brings capability-aware stage boundaries and pipeline configuration to service composition.

This paper describes how to model secure service workflows, enforce capability contracts, and publish pipeline manifests for distributed microservices.

The result is a service architecture where both dataflow and authority are explicit and reviewable."""

SECTIONS = [
    ('1. Pipeline-Driven Microservices', [
        'Microservices are often designed as independent stages in a larger workflow. Lateralus naturally maps service interactions to pipeline stages, preserving the flow of data and authority.',
        'This paper explores how capability-based access control and pipeline semantics combine to produce secure distributed services.',
        'The result is a service architecture where both the dataflow and the security model are explicit and reviewable.',
        'We explain why a capability-aware pipeline model reduces the risk of privilege escalation and unintended authority leakage in service compositions.',
    ]),
    ('2. Capability Contracts at Stage Boundaries', [
        'Each microservice stage declares the capabilities it requires and the capabilities it relinquishes. Lateralus encodes these declarations in the pipeline manifest.',
        'The compiler verifies that the composed workflow does not grant excessive authority and that service boundaries are respected.',
        'Capability contracts specify the resource and network privileges needed by each stage, making authority explicit in the published artifact.',
        'This section defines the contract language and the validation rules for capability-safe composition.',
    ]),
    ('3. Secure Service Composition', [
        'Service composition becomes secure when the pipeline semantics and capability constraints are both explicit. Lateralus allows pipeline authors to compose services while preserving least authority.',
        'The compiler can enforce that sensitive data flows only through authorized stages and that services cannot access capabilities outside their contract.',
        'This approach reduces the attack surface of distributed systems by limiting each stage to the minimal capabilities it needs.',
        'The section also describes how to perform capability-aware refactoring when a pipeline evolves over time.',
    ]),
    ('4. Case Study: Secure Telemetry Pipeline', [
        'We describe a telemetry pipeline where edge devices collect data, sanitize it, sign it, and forward it to a cloud aggregator.',
        ('code', 'let telemetry = read_sensor() |> redact_sensitive() |> sign_payload() |> dispatch_cloud()'),
        'The manifest records the capabilities required by each stage, including signing keys and network endpoints.',
        'This case study shows how capability-aware pipelines can enforce security and provenance end-to-end.',
    ]),
    ('5. Distributed Manifest Semantics', [
        'In a distributed microservice pipeline, the manifest spans multiple services and hosts. Lateralus supports distributed manifests that describe the service graph, capability flow, and trust boundaries.',
        'The compiler generates a manifest bundle that can be validated by deployment tools and auditors.',
        'This section explains how the distributed manifest preserves the semantics of the composed workflow.',
        'We also discuss how manifest consistency checks prevent outdated capability assignments from being deployed.',
    ]),
    ('6. Runtime Enforcement and Auditing', [
        'Runtime enforcement ensures that capabilities are used as declared. Lateralus can generate runtime checks for capability grants, service delegation, and audit logging.',
        'Auditors can then reconcile observed service interactions with the published pipeline manifest.',
        'This improves confidence in distributed service deployments.',
        'We describe how runtime telemetry can be aligned with pipeline stages to support post-incident analysis.',
    ]),
    ('7. Service Delegation and Least Authority', [
        'Capability-based microservices often delegate work to other services. Lateralus models delegation as explicit pipeline handoff points, making authority transfer visible.',
        'The compiler ensures that delegation does not implicitly expand a service’s capabilities beyond what the manifest permits.',
        'We discuss common delegation patterns and their implications for least-authority design.',
        'This section also explains how capability revocation and expiration can be represented in pipeline manifests.',
    ]),
    ('8. Related Work', [
        'There are capability-based systems and service mesh technologies, but few that marry capabilities with pipeline-first semantics at the language level.',
        'We compare Lateralus to these systems and highlight the benefits of explicit pipeline manifests for secure microservices.',
        'The section explains how capability-aware pipeline composition differs from conventional RBAC and network policy models.',
        'We show why pipeline semantics are especially useful for auditability and reasoning about authority flow in distributed systems.',
    ]),
    ('9. Deployment and Operational Guidance', [
        'Deployment of capability-aware pipelines requires manifest validation, service discovery, and consistent capability propagation across environments.',
        'We describe operational practices for deploying Lateralus microservices securely, including manifest signing and runtime validation.',
        'This section addresses the challenges of rolling updates, capability rotation, and staged deployment in distributed settings.',
        'It also includes practical advice for auditing deployed service graphs against the published pipeline manifest.',
    ]),
    ('10. Future Work', [
        'Future directions include fully automated capability inference, integration with decentralized identity systems, and support for encrypted pipeline payloads.',
        'We also propose research on adaptive capability contracts that evolve safely as services are upgraded.',
        'Another direction is richer tooling for visualizing authority flow and for verifying capability compliance in heterogeneous stacks.',
        'The conclusion emphasizes that explicit capability-aware pipelines are a natural fit for secure service composition.',
    ]),
    ('11. Manifest Composition for Multi-Service Workflows', [
        'Multi-service pipelines require manifests that span services, hosts, and trust boundaries. Lateralus supports distributed manifest bundles as first-class artifacts.',
        'The compiler can emit a coordinated manifest set that describes both data flow and capability flow across the composed system.',
        'This section also explains how to validate that the combined manifest satisfies least-authority and separation-of-duty constraints.',
    ]),
    ('12. Dynamic Delegation and Revocation', [
        'Dynamic delegation is common in microservices, but it must be explicit to avoid hidden authority escalation.',
        'Lateralus models delegation as a pipeline handoff with capability transfer semantics that are recorded in the manifest.',
        'The language also supports revocation points and expiry semantics so runtime systems can safely reclaim delegated authority.',
        ('code', 'let payment = authorize() |> issue_token() |> delegate_processor() |> revoke_on_timeout()'),
        'This section discusses how to preserve auditability when services delegate work dynamically in a capability-safe way.',
    ]),
    ('13. Operational Deployment Patterns', [
        'Deployment of capability-aware pipelines must handle service onboarding, manifest signing, and runtime capability validation.',
        'Lateralus enables deployment tooling to verify that each service receives only the capabilities it needs and nothing more.',
        'This section describes patterns for rolling updates, capability rotation, and service-level isolation in distributed environments.',
        'It also covers how to preserve manifest integrity across upgrades and how to recover safely from invalid capability assignments.',
    ]),
    ('Appendix A: Capability Patterns', [
        'Appendix A describes capability patterns for common service workflows, including delegation, least privilege, and capability revocation.',
        ('list', [
            'Delegation with minimal authority',
            'Least-privilege service stages',
            'Revocation and expiration patterns',
            'Audit-friendly capability flows',
        ]),
        'The appendix explains how these patterns can be expressed in Lateralus pipeline manifests.',
        'It also includes guidance for choosing the right capability pattern based on service trust boundaries.',
    ]),
    ('Appendix B: Service Security Guidelines', [
        'This appendix provides deployment guidance for capability-aware pipeline services, including manifest validation, service onboarding, and audit trail retention.',
        'It also discusses how to handle capability rotation and service updates safely.',
        'The appendix includes practical notes on logging, anomaly detection, and least-authority debugging.',
        'Finally, it covers how to preserve capability evidence across upgrades and how to recover from revoked service grants.',
    ]),
    ('Appendix C: Extended Notes', [
        'Capability flow is a natural complement to pipeline flow: authority should move along the same graph as data.',
        'A common mistake is to treat capabilities as an afterthought; this paper argues they belong in the pipeline source.',
        'Explicit service boundary semantics make it easier to reason about multi-service failure modes and least-authority violations.',
        'The manifest can help detect when service compositions inadvertently broaden the authority footprint of a workflow.',
        'Runtime audits are stronger when they can compare live capability use against the published pipeline manifest.',
        'Capability-aware pipelines are especially valuable in highly-regulated environments where authority must be provably limited.',
        'The paper shows that service mesh concepts can be expressed directly in a language-level pipeline model.',
        'Designing with capability contracts encourages developers to separate data transformation from authority handling.',
        'A key observation is that explicit capability stages reduce coupling between services and simplify refactoring.',
        'The manifest should be the source of truth for both what data flows where and what authority flows with it.',
    ]),
    ('Appendix D: Practical Considerations', [
        'Capability-aware service pipelines should encode authority transitions explicitly rather than relying on ambient permissions.',
        'Service onboarding should include manifest validation to ensure that capability requests are consistent with declared trust zones.',
        'Runtime service discovery must preserve the capability boundaries declared in the pipeline manifest.',
        'Use short-lived capability tokens and explicit delegation points for temporary cross-service operations.',
        'Audit logs are most useful when they record both the pipeline stage and the capabilities exercised by that stage.',
        'Capability rotation and revocation policies must be part of the deployment plan for secure microservices.',
        'Manifest bundles should include service-level capability summaries as well as the detailed stage contract information.',
        'In multi-tenant environments, capability manifests can document resource isolation boundaries and access policies.',
        'The pipeline language should make it easy to express whether a stage can forward capabilities to a downstream service.',
        'Design capability-safe service graphs so that each stage only receives the minimal authority it needs to perform its work.',
    ]),
    ('Appendix E: Extended Observations', [
        'Capability flow is a natural complement to pipeline flow: authority should move along the same graph as data.',
        'A common mistake is to treat capabilities as an afterthought; this paper argues they belong in the pipeline source.',
        'Explicit service boundary semantics make it easier to reason about multi-service failure modes and least-authority violations.',
        'The manifest can help detect when service compositions inadvertently broaden the authority footprint of a workflow.',
        'Runtime audits are stronger when they can compare live capability use against the published pipeline manifest.',
        'Capability-aware pipelines are especially valuable in highly-regulated environments where authority must be provably limited.',
        'The paper shows that service mesh concepts can be expressed directly in a language-level pipeline model.',
        'Designing with capability contracts encourages developers to separate data transformation from authority handling.',
        'A key observation is that explicit capability stages reduce coupling between services and simplify refactoring.',
        'The manifest should be the source of truth for both what data flows where and what authority flows with it.',
    ]),    ('Appendix F: Operational Capability Patterns', [
        'This appendix describes practical capability patterns for operations, such as service delegation, tenant isolation, and capability rotation.',
        'We show how capability manifests can make service-onboarding safer by codifying authority boundaries before deployment.',
        'The appendix also covers runtime practices for logging capability use and for reconciling actual service interactions with the published manifest.',
        'A capability-aware operations checklist should include manifest validation, authority revocation, and safe fallback strategies.',
        'We describe how to model temporary elevated authority and how to revoke it safely in a distributed pipeline graph.',
        'These patterns are designed to reduce the risk of unintended privilege expansion in complex service compositions.',
    ]),
    ('Appendix G: Incident Recovery and Revocation', [
        'Incident recovery in capability-aware pipelines should be guided by the manifest to avoid restoring excessive authority.',
        'This appendix explains how revocation semantics can be expressed in the pipeline source and how runtime systems can enforce them.',
        'We also discuss the role of audit trails in supporting post-incident reviews of capability usage and delegation decisions.',
        'The appendix emphasizes the importance of preserving manifest integrity during recovery, so the system can revert to a safe state.',
        'A key pattern is to treat revocation as a first-class pipeline event with clear semantics for downstream stage behavior.',
        'These notes are intended to help teams build resilient distributed pipelines that remain secure under failure conditions.',
    ]),    ('Appendix H: Zero-Trust Deployment Patterns', [
        'Zero-trust deployments demand that capability assumptions are explicit, verifiable, and minimally scoped.',
        'This appendix describes patterns for expressing zero-trust service boundaries in the pipeline manifest.',
        'We cover how to handle service discovery, capability propagation, and runtime attestation in a capability-aware pipeline.',
        'The manifest can serve as the zero-trust policy document for a distributed service graph.',
        'A useful pattern is to make capability elevation and delegation explicit events in the pipeline source.',
        'We also describe how to validate that runtime service interactions adhere to the published manifest in a zero-trust environment.',
        'These patterns help reduce implicit trust assumptions and make service-level security more robust.',
        'The appendix is aimed at teams building high-assurance cloud-native and edge service pipelines.',
    ]),
    ('Appendix I: Capability Rotation Playbooks', [
        'Capability rotation is a key operational requirement for secure distributed services.',
        'This appendix describes playbooks for rotating service credentials, key material, and delegated authority safely.',
        'We explain how to model rotation semantics in the pipeline manifest so the system can continue operating during the transition.',
        'The appendix also covers rollback strategies and how to recover safely from failed rotation attempts.',
        'A good playbook keeps the authority graph consistent and prevents accidental privilege widening during rotation.',
        'We also describe how to preserve audit evidence of rotation actions and how to reconcile live capability use with the manifest.',
        'These playbooks are especially important for services operating under strict regulatory or compliance constraints.',
        'The appendix emphasizes that rotation should be treated as an ongoing operational activity, not a one-time event.',
    ]),    ('Appendix J: Runtime Capability Reference', [
        'This appendix provides a practical runtime reference for capability-aware microservice pipelines.',
        'It includes patterns for capability validation, revocation, and audit logging in distributed service graphs.',
        'We describe how to preserve manifest integrity through runtime capability rotations and service updates.',
        'The reference also covers how to map runtime telemetry to pipeline stages and capability flows.',
        'We include guidance on handling transient authority delegation safely and on recovering from failed revocations.',
        'The appendix emphasizes the importance of making capability transitions explicit in the pipeline source.',
        'We also describe how to keep runtime enforcement aligned with the published manifest in multi-tenant environments.',
        'The reference notes how to avoid authority creep through explicit service boundary and delegation semantics.',
        'It includes advice for maintaining capability evidence across rolling updates and service migration.',
        'This appendix should help teams build more robust and auditable capability-aware deployments.',
    ]),    ('Appendix K: Capability Operations Field Guide', [
        'This field guide provides practical operational patterns for capability-aware distributed pipelines.',
        'It covers manifest validation, runtime capability use tracking, and safe delegation workflows.',
        'The guide includes recommendations for handling capability rotation, expiry, and revocation in live services.',
        'We also describe how to keep the authority graph explicit as services evolve and as deployments change.',
        'A useful pattern is to encode operational policies directly in the pipeline manifest so they remain part of the source artifact.',
        'The appendix explains how to reconcile observed capability use with the published manifest during incident review.',
        'It also offers guidance on safe recovery from capability leaks and unexpected authority elevation.',
        'The field guide includes advice for making audit trails useful without imposing excessive runtime overhead.',
        'We describe how to use pipeline-aware telemetry to support post-deployment compliance and forensics.',
        'It also covers how to build manifest-driven automation for capability provisioning and deprovisioning.',
        'The appendix emphasizes the importance of preserving least-authority principles even as the service graph scales.',
        'Finally, it positions the manifest as the central operational contract for secure microservices.',
    ]),    ('Appendix L: Capability Lifecycle Guide', [
        'This guide covers the operational lifecycle of capabilities in distributed pipeline systems.',
        'It explains how to rotate, revoke, and reissue capabilities without breaking live service dependencies.',
        'The guide includes patterns for documenting capability lifecycles in the manifest and runtime logs.',
        'We also describe how to validate capability handoff between services in a way that is both auditable and safe.',
        'A key recommendation is to treat capability expiration as a first-class state transition.',
        'This makes it easier to reason about live delegation and about the consequences of stale authority.',
        'The appendix also covers fallback behavior when capabilities are unavailable or partially revoked.',
        'It includes advice for ensuring rollback plans preserve least-authority guarantees.',
        'We discuss how to keep capability telemetry readable for incident responders and auditors.',
        'The guide also summarizes how to use manifest-driven automation to refresh capabilities safely.',
        'It recommends keeping capability policies explicit and versioned alongside pipeline source.',
        'Finally, the appendix emphasizes that secure capability operations depend on clear, observable contracts.',
    ]),
]

if __name__ == '__main__':
    render_paper(
        out_path=OUT,
        title=TITLE,
        subtitle=SUBTITLE,
        meta=META,
        abstract=ABSTRACT,
        sections=SECTIONS,
    )
