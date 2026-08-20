enum BusinessCapabilityFamily {
  executiveEnterpriseIntelligence('BCF01'),
  operations('BCF02'),
  financeCostIntelligence('BCF03'),
  growthMarketing('BCF04'),
  commerceSales('BCF05'),
  researchData('BCF06');

  const BusinessCapabilityFamily(this.contextCode);

  final String contextCode;
}

/// Bounded display/request metadata only.
///
/// A business-capability family may help preserve the user's operating context,
/// but it is never embedded into the free-form objective and never selects a
/// provider, worker, route, tenant, approval, tool, validation or execution
/// authority. Those decisions remain exclusively backend-governed.
class BusinessCapabilityContext {
  const BusinessCapabilityContext(this.family);

  final BusinessCapabilityFamily family;

  String get contextCode => family.contextCode;
}
