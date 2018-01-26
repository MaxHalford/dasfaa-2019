from scipy.stats import chi2_contingency


def calc_mutual_info(x, y, bins='sqrt'):
    """Calculates the mutual information between two series."""

    if bins == 'sqrt':
        bins = math.ceil(math.log(len(x)))

    counts = np.histogram2d(x, y, bins)[0]
    g, p, dof, expected = chi2_contingency(counts, lambda_='log-likelihood')
    mi = 0.5 * g / counts.sum()
    return mi
