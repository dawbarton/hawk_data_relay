function hawk_send(values, url)
% HAWK_SEND  Send a command to the MCU via hawk-data-relay.
%
%   HAWK_SEND(VALUES) sends VALUES as a COBS-encoded float32 array to the MCU.
%
%   VALUES  — 1 x M numeric vector of float values
%   URL     — (optional) relay base URL, default 'http://localhost:5000'
%
%   Example:
%     hawk_send([1.0, 0.5, 0.0]);

    if nargin < 2
        url = 'http://localhost:5000';
    end

    opts = weboptions('MediaType', 'application/json', 'RequestMethod', 'post');
    webwrite([url '/command'], struct('values', values(:)'), opts);
end
