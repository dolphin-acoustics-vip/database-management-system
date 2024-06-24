class Selection:

    freq_max: float # DONE
    freq_min: float # DONE
    duration: float
    freq_begin: float # DONE
    freq_end: float # DONE
    freq_range: float # DONE
    dc_mean: float
    dc_standarddeviation: float
    freq_mean: float # DONE
    freq_standarddeviation: float # DONE
    freq_median: float # DONE
    freq_center: float # DONE
    freq_relbw: float # DONE
    freq_maxminratio: float # DONE
    freq_begendratio: float # DONE
    freq_quarter1: float # DONE
    freq_quarter2: float # DONE
    freq_quarter3: float # DONE
    freq_spread: float # DONE
    dc_quarter1mean: float
    dc_quarter2mean: float
    dc_quarter3mean: float
    dc_quarter4mean: float
    freq_cofm: float
    freq_stepup: int # DONE
    freq_stepdown: int # DONE
    freq_numsteps: int # DONE
    freq_slopemean: float # DONE
    freq_absslopemean: float # DONE
    freq_posslopemean: float # DONE
    freq_negslopemean: float # DONE
    freq_sloperatio: float # DONE
    freq_begsweep: int # DONE
    freq_begup: int # DONE
    freq_begdown: int # DONE
    freq_endsweep: int # DONE - DISREP
    freq_endup: int # DONE
    freq_enddown: int # DONE
    num_sweepsupdown: int # DONE
    num_sweepsdownup: int # DONE
    num_sweepsupflat: int # DONE
    num_sweepsdownflat: int # DONE
    num_sweepsflatup: int # DONE
    num_sweepsflatdown: int # DONE
    freq_sweepuppercent: float # DONE
    freq_sweepdownpercent: float # DONE
    freq_sweepflatpercent: float # DONE
    num_inflections: int # DONE
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