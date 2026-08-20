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

/// One-shot Desktop presentation handoff for optional business context.
///
/// This is not an execution authority. The value is consumed exactly once by
/// the authenticated Desktop submission path and is cleared on failed/finished
/// submissions and sign-out so context cannot leak into a later request.
class BusinessCapabilitySubmissionBus {
  BusinessCapabilitySubmissionBus._();

  static BusinessCapabilityContext? _pending;

  static BusinessCapabilityContext? get pending => _pending;

  static void stage(BusinessCapabilityContext? context) {
    _pending = context;
  }

  static BusinessCapabilityContext? take() {
    final context = _pending;
    _pending = null;
    return context;
  }

  static void clear() {
    _pending = null;
  }
}
