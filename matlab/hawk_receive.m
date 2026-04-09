function [data, timestamps] = hawk_receive(ms, url)
% HAWK_RECEIVE  Pull recent data from hawk-data-relay.
%
%   [DATA, TIMESTAMPS] = HAWK_RECEIVE(MS) returns the last MS milliseconds
%   of data as a numeric matrix.
%
%   DATA        — N x num_floats double matrix (one row per frame)
%   TIMESTAMPS  — N x 1 double vector of Unix timestamps (seconds)
%   MS          — duration to request in milliseconds (positive integer)
%   URL         — (optional) relay base URL, default 'http://localhost:5000'
%
%   Example:
%     [data, t] = hawk_receive(5000);

    if nargin < 2
        url = 'http://localhost:5000';
    end

    response = webread([url '/data'], 'ms', ms);

    if isempty(response)
        data       = zeros(0, 0);
        timestamps = zeros(0, 1);
        return
    end

    % webread returns a struct when there is one frame, struct array otherwise
    if ~isstruct(response)
        data       = zeros(0, 0);
        timestamps = zeros(0, 1);
        return
    end

    timestamps = [response.t]';
    data       = vertcat(response.values);
end
