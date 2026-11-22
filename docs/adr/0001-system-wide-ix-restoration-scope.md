# ADR 0001: System-wide 325iX restoration scope

Status: Accepted  
Date: 2026-11-22  
Decision owner: Vehicle owner / Product Owner

## Context

The front axle was selected as the first end-to-end proving case. Incremental delivery risked turning that proving case into the product boundary, while the intended product covers the complete high-priority mechanical and electrical 325iX.

## Decision

The product is organized around system-wide restoration domains: AWD/drivetrain, suspension/steering, brakes, engine/cooling/fuel, manual transmission/clutch, electrical/controls and climate/visibility. Front axle remains a mission template inside suspension/steering.

Bodywork, trim, seats, accessories, retrofits and entertainment remain catalog-searchable but are deferred from default product prioritization. They may be promoted only through an explicit priority decision.

Every priority domain uses the shared mission, evidence, specialist, work-order, QA and digital-twin contracts. A domain-specific workflow may extend those contracts but cannot create an isolated parallel product.

## Consequences

- The Garage and active mission become the primary experience.
- Release gates must demonstrate cross-domain mission creation and persistence.
- Front-axle-specific APIs remain compatible until generalized consumers replace them.
- Research automation continues across all catalog systems while product sequencing prioritizes P0 domains.
- Safety clearance remains specific to a vehicle, component, procedure, measurements and qualified sign-off.

