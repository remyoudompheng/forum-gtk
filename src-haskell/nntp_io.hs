-- Interface NNTP
module Nntp_Io
    where

import Network
import System.IO
import System.IO.Unsafe

host = "clipper.ens.fr"
port = PortNumber 2019

data NNTPConnection = NNTPConnection {
    reader :: IO String,
    writer :: Handle
}

nntp_init :: String -> PortID -> IO NNTPConnection
nntp_init host port = 
    let readChars :: Handle -> IO String
        readChars h = do
            c <- hGetChar h
            next <- unsafeInterleaveIO $ readChars h
            return (c : next)
    in
    do
    handle <- connectTo host port
    hSetBuffering handle LineBuffering
    let nntp = NNTPConnection {
        reader = readChars handle,
        writer = handle }
    return nntp
