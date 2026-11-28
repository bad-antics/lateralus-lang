def poisson_pmf(k: int, lam: float) -> float:
    """
    Compute the Poisson probability mass function P(X=k) with mean λ.
    
    Uses log-space calculation to avoid overflow from computing lam**k directly.
    Formula: P(k; λ) = e^(-λ + k*ln(λ) - ln(k!))
    where lgamma(k+1) = ln(k!)
    
    Args:
        k: The number of events
        lam: The mean (expected value) of the Poisson distribution
        
    Returns:
        The probability of observing exactly k events
        
    Examples:
        >>> poisson_pmf(200, 200.0)
        0.02819772768592082
    """
    if lam <= 0 or k < 0:
        return 0.0
    if k == 0:
        return math.exp(-lam)
    
    # Compute in log space to avoid overflow from lam**k
    # P(k; λ) = exp(-λ + k*ln(λ) - ln(k!))
    log_pmf = (-lam + k * math.log(lam) - math.lgamma(k + 1))
    return math.exp(log_pmf)