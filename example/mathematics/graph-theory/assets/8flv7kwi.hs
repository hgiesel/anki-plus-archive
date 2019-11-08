module StateTest () where

import Control.Monad.State

data DimmerState = S0 | S1 | S2 | S3
  deriving (Show, Eq, Ord)

omega :: DimmerState -> (String, DimmerState)
omega S0 = ("It's off", S0)
omega S1 = ("It's dim", S1)
omega S2 = ("It's medium", S2)
omega S3 = ("It's bright", S3)

click :: DimmerState -> (String, DimmerState)
click S0 = ("It's dim now", S1)
click S1 = ("It's medium now", S2)
click S2 = ("It's bright now", S3)
click S3 = ("It's off now", S0)

omegaS :: State DimmerState String
omegaS = state omega

clickS :: State DimmerState String
clickS = state click

clickFourTimes :: State DimmerState String
clickFourTimes = do clickS
                    clickS
                    clickS
                    clickS

clickAndReset :: State DimmerState [String]
clickAndReset = do x <- clickS
                   put S0      -- reset
                   y <- clickS
                   return [x, y]

-- e.g.
-- runState (clickS >> clickS >> clickS ) S0
