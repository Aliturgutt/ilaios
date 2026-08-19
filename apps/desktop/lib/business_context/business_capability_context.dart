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

/// Adds a bounded, opaque business-context marker without naming a provider,
/// worker, route, approval, tool, tenant or execution authority.
///
/// The canonical backend still classifies and admits the ordinary user
/// objective. The opaque code exists only so the governed request can retain
/// optional business context without teaching the Desktop how to route work.
String withBusinessCapabilityContext(
  String objective,
  BusinessCapabilityFamily? family,
) {
  if (family == null) return objective;
  return '$objective\n\n[ILAIOS_BUSINESS_CONTEXT:${family.contextCode}]';
}
