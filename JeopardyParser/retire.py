  # * Make a list of all 3 letter Eng words
  L3n = [w for w in norvig_d if len(w)==3]
  L3w = [w for w in eng_d if len(w)==3]
  print "3 L words:", len(L3w), "Norvig:", len(L3n)

  #diffwords = [w for w in L3n if w not in L3w]

  #L3 = list(set(L3n + L3w)) #consolidate uniques

