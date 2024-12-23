import numpy as np
from scipy import signal
from sklearn.base import BaseEstimator, TransformerMixin


class Transformer(BaseEstimator, TransformerMixin):
    '''
    Base class for transformers providing dummy implementation
        of the methods expected by sklearn
    '''
    def fit(self, x, y=None):
        return self


class ButterFilter(Transformer):
    '''Applies Scipy's Butterworth filter'''
    def __init__(self, sampling_rate: int, order: int, highpass: int, lowpass: int) -> None:
        self.sampling_rate = sampling_rate
        self.order = order
        self.highpass = highpass
        self.lowpass = lowpass

        normal_cutoff = [a / (0.5 * self.sampling_rate) for a in (self.highpass, self.lowpass)]
        self.filter = signal.butter(self.order, normal_cutoff, btype='bandpass')

    def transform(self, x):
        out = np.empty_like(x)
        out[:] = [signal.filtfilt(*self.filter, item) for item in x]
        return out


class Decimator(Transformer):
    def __init__(self, factor: int):
        '''
        factor: downsampling factor, shouldn't be more than 13,
            see :py:funct:`scipy.signal.decimate` for more info
        '''
        self.factor = factor

    def transform(self, x):
        '''
        Args:
            x: iterable of np.ndarrays
        Returns:
            np.ndarray of np.objects shaped (len(x), )
                In other words it outputs ndarray of objects each of which is
                result of decimation of items from x
        '''
        out = np.empty(len(x), dtype= object)
        out[:] = [signal.decimate(item, self.factor) for item in x]
        return out
class ChannellwiseScaler(Transformer):
    '''Performs channelwise scaling according to given scaler'''
    def __init__(self, scaler: Transformer):
        '''
        Args:
            scaler: instance of one of sklearn.preprocessing classes
                StandardScaler or MinMaxScaler or analogue
        '''
        self.scaler = scaler

    def fit(self, x: np.ndarray, y=None):
        '''
        Args:
            x: array of eegs, that is every element of x is (n_channels, n_ticks)
                x shaped (n_eegs) of 2d array or (n_eegs, n_channels, n_ticks)
        '''
        # Ensure x is a 3D array
        if x.ndim == 2:
            x = x[np.newaxis, ...]

        # Reshape data for fitting
        n_samples = x.shape[0] * x.shape[2]  # total number of time points across all samples
        n_channels = x.shape[1]
        
        # Reshape to (n_samples, n_channels)
        reshaped_data = np.vstack([signals.T for signals in x])
        self.scaler.fit(reshaped_data)
        
        return self

    def transform(self, x):
        '''
        Scales each channel.
        Works either with one record, 2-dim input, (n_channels, n_ticks)
        or many records 3-dim, (n_records, n_channels, n_samples)
        Returns the same format as input
        '''
        original_shape = x.shape
        is_2d = x.ndim == 2
        
        # Convert 2D input to 3D
        if is_2d:
            x = x[np.newaxis, ...]
        
        scaled = np.empty_like(x)
        for i, signals in enumerate(x):
            # Reshape to 2D for scaling
            reshaped = signals.T
            # Scale and reshape back
            scaled[i] = self.scaler.transform(reshaped).T
        
        # Return in original format
        return scaled[0] if is_2d else scaled


class MarkersTransformer(Transformer):
    '''Transforms markers channels to arrays of indexes of epoch start and labels
    '''
    def __init__(self, labels_mapping: dict, decimation_factor: int=1, empty_label: float=0.):
        self.labels_mapping = labels_mapping
        self.decimation_factor = decimation_factor
        self.empty_label = empty_label

    def transform(self, batch):
        res = []
        for markers in batch:
            index_label = []
            for index, label in enumerate(markers):
                if label == self.empty_label: continue
                index_label.append([
                    index // self.decimation_factor,
                    self.labels_mapping[label],
                ])
            res.append(np.array(index_label, dtype=np.int))
        return res
