enum BusinessCapabilityFamily {
  executiveEnterpriseIntelligence('executive_enterprise_intelligence'),
  operations('operations'),
  financeCostIntelligence('finance_cost_intelligence'),
  growthMarketing('growth_marketing'),
  commerceSales('commerce_sales'),
  researchData('research_data');

  const BusinessCapabilityFamily(this.wireValue);

  final String wireValue;
}

/// Transient, process-local metadata handoff for the existing one-prompt path.
///
/// This value is descriptive intent context only. It does not carry tenant,
/// provider, worker, route, approval, grant, tool, validation or execution
/// authority. [CreateView] clears it after each submission attempt and the
/// authenticated backend validates the exact allowlist independently.
abstract final class BusinessCapabilitySubmissionBus {
  static BusinessCapabilityFamily? pending;

  static void clear() => pending = null;
}
