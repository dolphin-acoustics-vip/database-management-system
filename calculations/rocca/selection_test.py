class Selection:

    freq_max: float
    freq_min: float
    duration: float
    freq_begin: float
    freq_end: float
    freq_range: float
    dc_mean: float
    dc_standarddeviation: float
    freq_mean: float
    freq_standarddeviation: float
    freq_median: float
    freq_center: float
    freq_relbw: float
    freq_maxminratio: float
    freq_begendratio: float
    freq_quarter1: float
    freq_quarter2: float
    freq_quarter3: float
    freq_spread: float
    dc_quarter1mean: float
    dc_quarter2mean: float
    dc_quarter3mean: float
    dc_quarter4mean: float
    freq_cofm: float
    freq_stepup: int
    freq_stepdown: int
    freq_numsteps: int
    freq_slopemean: float
    freq_absslopemean: float
    freq_posslopemean: float
    freq_negslopemean: float
    freq_sloperatio: float
    freq_begsweep: int
    freq_begup: int
    freq_begdown: int
    freq_endsweep: int
    freq_endup: int
    freq_enddown: int
    num_sweepsupdown: int
    num_sweepsdownup: int
    num_sweepsupflat: int
    num_sweepsdownflat: int
    num_sweepsflatup: int
    num_sweepsflatdown: int
    freq_sweepuppercent: float
    freq_sweepdownpercent: float
    freq_sweepflatpercent: float
    num_inflections: int
    inflection_maxdelta: float
    inflection_mindelta: float
    inflection_maxmindelta: float
    inflection_meandelta: float
    inflection_standarddeviationdelta: float
    inflection_duration: float
    step_duration: float
    freq_peak: float
    bw3db: float
    bw3dblow: float
    bw3dbhigh: float
    bw10db: float
    bw10dblow: float
    bw10dbhigh: float
    rms_signal: float
    rms_noise: float
    snr: float
    num_crossings: int
    sweep_rate: float
    mean_timezc: float
    median_timezc: float
    variance_timezc: float
    whale_train: int

    def __init__(self):
        pass