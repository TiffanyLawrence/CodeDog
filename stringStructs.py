# CodeDog Program Maker
#   This file is code to convert "string" style structures into 'struct' style structures.

import re
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr

def codeDogTypeToString(classes, tags, field):
    #print "FIELD:", field
    S=''
    fieldName=field['fieldName']
    fieldType=progSpec.getFieldType(field)
    fieldValue =field['value']
    fieldOwner =field['owner']
    if(fieldType == 'flag'):
        if fieldValue!=None and fieldValue!=0 and fieldValue!='false':
            S+='flag: ' + fieldName + ' <- true\n'
        else: S+='flag: ' + fieldName +'\n'
    elif fieldType=='mode':
        if fieldValue!=None:
            S+='mode ['+field['enumList']+']: ' + fieldName + ' <- '+fieldValue+'\n'
        else: S+='mode ['+field['enumList']+']: ' + fieldName +'\n'
    elif fieldOwner=='const':
        #print 'const ', fieldType, ': ', fieldName, ' <- ',fieldValue
        #S+='const '+fieldType+': ' + fieldName + ' <- '+fieldValue+'\n'
        pass
    elif fieldOwner=='const':
        print("Finish This")

    return S

rules=[]
constDefs=[]
ruleSet={}      # Used to track duplicates
globalFieldCount=0
globalTempVarIdx=0

def genParserCode():
    global rules
    global constDefs
    RuleList=''
    for rule in rules:
        if rule[1]=='term':
            RuleList+='        addTerminalProd("' + rule[0] +'", ' + rule[2] + ', "' + str(rule[3]).replace('::','_') + '")\n'
        elif rule[1]=='nonterm':
            RuleList+='        addNon_TermProd("' + rule[0] +'", ' + rule[2] + ', ' + str(rule[3]).replace('::','_')  + ')\n'

    ConstList=''
    for C in constDefs:
        ConstList+='    const int: ' + C[0].replace('::','_') + ' <- ' + str(C[1]) + '\n'

    code= r"""

struct production{
    flag: isTerm
    mode[parseSEQ, parseALT, parseREP, parseOPT, parseAUTO]: prodType
    me string: constStr
    me int[list]: items
    void: printProd(me int: SeqPos, me int: originPos, me string[their list]: rnames) <- {
        me int: ProdType <- prodType
        me string: ProdStr <- ""
        print("[")
        if     (ProdType==parseALT) {ProdStr<-"ALT"}
        else if(ProdType==parseAUTO){ProdStr<-"Aut"}
        else if(ProdType==parseSEQ) {ProdStr<-"SEQ"}
        else if(ProdType==parseREP) {ProdStr<-"REP"}
        print(ProdStr, " from slot:", originPos, ": ")
        if(isTerm){
            if(SeqPos==0) {print(" > ")}
            print('"', constStr,'"')
            if(SeqPos>0) {print(" > ")}
        } else {
            if(ProdType==parseALT and SeqPos==0) {print(" > ")}
            withEach p in items {
                if(ProdType == parseSEQ and p_key == SeqPos){ print(" > ")}
                if(p_key!=0){
                    if(ProdType==parseALT){print("| ")}
                }
                if(ProdType==parseREP and p_key>0){ print(p, " ")}
                else {print(rnames[p], " ")}
            }
            if(ProdType==parseREP){ print('(Len:%i`SeqPos`)')}
            else {if (((p_key == SeqPos and ProdType == parseSEQ) or (ProdType==parseALT and SeqPos>0))) {print(" > ")}}
        }
        print("] ")
    }
}

struct pedigree{
    our stateRec: pred
    our stateRec: cause
    me int: productionID
}

struct stateRec{
    me int: productionID
    me int: SeqPosition
    me int: originPos
    me int: crntPos
    me pedigree[list]: pedigrees
    our stateRec: next
    our stateRec: child
    //void: print(their production: prod) <- {prod.printProd(SeqPosition, originPos)}
    void: printSREC(their EParser: EP) <- {
        their production: prod <- EP.grammar[productionID]
        prod.printProd(SeqPosition, originPos, EP.rnames)}
}
struct stateRecPtr{our stateRec: stateRecPtr}

struct stateSets{
    me stateRecPtr[list]: stateRecs
    me uint: flags
    //stateSets():flags(0){}
}

struct EParser{
    me string: textToParse
    me int: startProduction
    me stateSets[list]: SSets
    me production[list]: grammar
    me bool: parseFound
    our stateRec: lastTopLevelItem
    me string: errorMesg
    me int: errLineNum
    me int: errCharPos
    me string[list]: rnames

    void: clearGrammar() <- {grammar.clear() rnames.clear()}
    void: addTerminalProd(me string: name, me int: ProdType, me string: s) <- {
        me production: P
        P.prodType <- ProdType
        P.isTerm   <- true
        P.constStr <- s
        grammar.pushLast(P)
        rnames.pushLast(name)
    }
    void: addNon_TermProd(me string: name, me int: ProdType, me int[list]: terms) <- {
        me production: P
        P.prodType <- ProdType
        P.items <- terms
        grammar.pushLast(P)
        rnames.pushLast(name)
    }

    void: dump() <- {
         withEach crntPos in RANGE(0 .. SSets.size()) {
            their stateSets: SSet <- SSets[crntPos]
            me string: ch <- "x"
            if(crntPos+1 != SSets.size()) {
                ch <- ""+textToParse[crntPos]
            }
         //   print("SLOT: ", crntPos, "(", ch, ") - size: ", SSet->stateRecs.size(), "\n")
            withEach SRec in SSet.stateRecs {
                their production: prod <- grammar[SRec.productionID]
                print("    ")
                SRec.printSREC(self)
                print("\n")
            }
        }
        if(parseFound){print("\nPARSE PASSED!\n\n")}
        else {print("\nPARSE failed.\n\n")}

    }

#CONST_CODE_HERE

    void: populateGrammar() <- {
        clearGrammar()
#GRAMMAR_CODE_HERE

    }

    me void: addProductionToStateSet(me int: crntPos, me int: productionID, me uint: SeqPos, me int: origin, our stateRec: pred, our stateRec: cause) <- {
        me bool: Duplicate <- false
        their production: prod <- grammar[productionID]
        me int: ProdType <- prod.prodType
        withEach item in SSets[crntPos].stateRecs { // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID and item.originPos==origin){
          //  print ("POSES", item.SeqPosition, ', ', SeqPos, "::")
                if(item.SeqPosition==SeqPos or (ProdType==parseREP and item.SeqPosition+1 == SeqPos)){
          //          print("############ DUPLICATE rule#", productionID, " at slot ", crntPos, ", POS:", SeqPos, "\n")
                    me pedigree: ped
                    ped.pred <- pred
                    ped.cause <- cause
                    ped.productionID <- productionID
                    item.pedigrees.pushLast(ped)
                    Duplicate <- true
                }
            }
        }

        me bool: thisIsTopLevelItem <- false
        if(productionID==startProduction and origin==0){
            thisIsTopLevelItem <- true
            if(SeqPos==prod.items.size()){
                parseFound <- true
             // TODO: investigate the cases where the line below prints. There could be a subtle bug.
               // print(" <PARSE PASSES HERE> ")
            }
        }

        if(!Duplicate){
            if(ProdType == parseSEQ or ProdType == parseREP or ProdType == parseALT or ProdType == parseAUTO){
                our stateRec: newStateRecPtr Allocate(newStateRecPtr)
                newStateRecPtr.productionID <- productionID
                newStateRecPtr.SeqPosition <- SeqPos
                newStateRecPtr.originPos <- origin
                newStateRecPtr.crntPos <- crntPos
                me pedigree: ped
                ped.pred <- pred
                ped.cause <- cause
                ped.productionID <- productionID
                newStateRecPtr.pedigrees.pushLast(ped)
                if(thisIsTopLevelItem) {lastTopLevelItem <- newStateRecPtr}
                SSets[crntPos].stateRecs.pushLast(newStateRecPtr)
  //              print("############ ADDING To SLOT ", crntPos, ":")
  //              newStateRecPtr.print(self)
                applyPartialCompletion(newStateRecPtr)
  //              print("\n")
            } //else {print("  Unknown ProductionType:", ProdType, "\n")}
        }

        if(ProdType == parseALT and SeqPos==0){
           // print("  ALT-LIST\n")
            withEach AltProd in prod.items {
   //             print("                                  ALT: ")
                addProductionToStateSet(crntPos, AltProd, 0, origin, pred, cause)
            }
        } else if(ProdType == parseAUTO and productionID == ws and SeqPos==0){  // Whitespace is nullable
            addProductionToStateSet(crntPos, productionID, 1, origin, pred, cause)
        }
    }

    me void: initPosStateSets(me int: startProd, me string: txt) <- {
       // print('Will parse "', txt, '" with rule ', startProd, '.\n')
        startProduction <- startProd
        textToParse <- txt
        SSets.clear()
        withEach i in RANGE(0 .. txt.size()+1){
            me stateSets: newSSet
            SSets.pushLast(newSSet)
        }
        addProductionToStateSet(0, startProduction, 0, 0, NULL, NULL)
    }


    me int: chkStr(me int: pos, me string: s) <- {
        me int: L <- s.size()
        if(pos+L > textToParse.size()){return(-1)}
        withEach i in RANGE(0 .. L){
            if( s[i] != textToParse[pos+i]) {
  //              print("                                 chkStr FAILED\n")
                return(-1)
            }
        }
  //      print("                                 chkStr PASSED\n")
        return(L)
    }

    me int: scrapeUntil(me int:pos, me string:endChar) <- {
        me char: ender <- endChar[0]
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(ch==ender){return(p-pos)}
        }
        return(-1)
    }

    me int: escapedScrapeUntil(me int:pos, me string:endChar) <- {
        me char: ch
        me string: prevCharStr <- " "
        me char: prevChar <- prevCharStr[0]
        me char: ender <- endChar[0]
        me int: txtSize <- textToParse.size()
        me string: escCharStr <- "\\ "
        me char: escChar <- escCharStr[0]
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(prevChar!=escChar and ch==ender){return(p-pos)}
            if(prevChar==escChar and ch==escChar) {prevChar<-escCharStr[1]}
            else {prevChar <- ch}
        }
        return(-1)
    }


    me int: scrapeAlphaSeq(me int: pos) <- {
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isalpha(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int: scrapeUintSeq(me int: pos) <- {
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isdigit(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int: scrapeHexNum(me int: pos) <- {
        me int: txtSize <- textToParse.size()
        me char: ch
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(!isxdigit(ch)){if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int: scrapeBinNum(me int: pos) <- {
        me int: txtSize <- textToParse.size()
        me char: ch
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(!isxdigit(ch)){if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int: scrapeAlphaNumSeq(me int: pos) <- {
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isalnum(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int: scrapeAlphaNum_Seq(me int: pos) <- {
        me char: ch
        me string: chars <- "_"
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isalnum(ch) or ch==chars[0]){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int: scrapePrintableSeq(me int: pos) <- {
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isprint(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int: scrapeWS(me int: pos) <- {
        me char: ch
        me int: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize){
            ch <- textToParse[p]
            if(isspace(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int: scrapeQuotedStr(me int: pos) <- {
        me string: ch <- ""
        ch <+- textToParse[pos]
        if(ch != "\'" and ch != "\""){return(-1)}
        else{pos <+- 1}
        me int: sLen <- escapedScrapeUntil(pos, ch)
        if(sLen<0){return(-1)}
        return(sLen+2)
    }

    me int: scrapeQuotedStr1(me int: pos) <- {
        if(chkStr(pos, "'")>=0){pos <- pos+1}else{return(-1)}
        me int: sLen <- escapedScrapeUntil(pos, "'")
        if(sLen<0){return(-1)}
        return(sLen+2)
    }

    me int: scrapeQuotedStr2(me int: pos) <- {
        if(chkStr(pos, "\"")>=0){pos <- pos+1}else{return(-1)}
        me int: sLen <- escapedScrapeUntil(pos, "\"")
        if(sLen<0){return(-1)}
        return(sLen+2)
    }
    me int: scrapeCID(me int: pos) <- {
        me int: txtSize <- textToParse.size()
        me string: chars <- "_"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(-1)
        }
        me char: ch <- textToParse[pos]
        if(isalpha(ch)){   // or ch==chars[0]){
            return(scrapeAlphaNum_Seq(pos))
        } else {return(-1)}
    }
    // TODO: me int: scrapeUniID(me int: pos) <- { }

    me int: scrapeIntSeq(me int: pos) <- {
        me char: ch <- textToParse[pos]
        me int: txtSize <- textToParse.size()
        me int: initialChars <- 0
        me string: chars <- "+-"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(-1)
        }
        if(ch==chars[0] or ch==chars[1]){ initialChars <- 1}
        return(scrapeUintSeq(pos)+initialChars)
    }
    // TODO: me int: scrapeRdxSeq(me int: pos) <- { }

    me int: scrapeToEOL(me int: pos) <- {
        return(scrapeUntil(pos, "\\n"))
    }
    me int: textMatches(me int: ProdID, me int: pos) <- {
        their production: Prod <- grammar[ProdID]
 //       print('    MATCHING "%s`Prod->constStr.data()`"... ')
        me int: prodType <- Prod.prodType
        if(prodType==parseSEQ){ //prod is simple text match
            return(chkStr(pos, Prod.constStr))
        } else{
            if(prodType==parseAUTO){
                switch(ProdID){
                    case alphaSeq:    {return(scrapeAlphaSeq(pos))}
                    case uintSeq:     {return(scrapeUintSeq(pos))}
                    case alphaNumSeq: {return(scrapeAlphaNumSeq(pos))}
                    case printables:  {return(scrapePrintableSeq(pos))}
                    case ws:          {return(scrapeWS(pos))}
                    case quotedStr:   {return(scrapeQuotedStr(pos))}
                    case quotedStr1:  {return(scrapeQuotedStr1(pos))}
                    case quotedStr2:  {return(scrapeQuotedStr2(pos))}
                    case HexNum_str:  {return(scrapeHexNum(pos))}
                    case BinNum_str:  {return(scrapeBinNum(pos))}
                    case BigInt:      {return(scrapeUintSeq(pos))}
                    case CID:         {return(scrapeCID(pos))}
             //       case UniID:       {return(scrapeUniID(pos))}
                    case intSeq:      {return(scrapeIntSeq(pos))}
             //       case RdxSeq:      {return(scrapeRdxSeq(pos))}
                    case toEOL:       {return(scrapeToEOL(pos))}
                    default: {print("Invalid AUTO-parse production type.\n")}
                }
            }
        }
        return(-1)
    }

    ///////////////// Late Completion Code
    //  This code handles the case where productions are added with the same origin (crntPos) as their (null) predecessor and must have completions applied from past completions.
    our stateRec[list]: SRecsToComplete
    me int: crntPos

    void: resetCompletions(me int: CrntPos) <- {
        SRecsToComplete.clear()
        crntPos <- CrntPos
    }

    void: registerCompletion(our stateRec: SRecToComplete) <- {
        SRecsToComplete.pushLast(SRecToComplete)
    }

    void: applyPartialCompletion(our stateRec: backSRec) <- {
        their production: backProd <- grammar[backSRec.productionID]
      //  print('                Checking New Item :') backSRec.print(self)
        me int: prodTypeFlag <- backProd.prodType
        me int: backSRecSeqPos <- backSRec.SeqPosition
        withEach SRec in SRecsToComplete{
            if(crntPos==SRec.originPos and !(backSRec.productionID==SRec.productionID and backSRec.SeqPosition==SRec.SeqPosition and backSRec.originPos==SRec.originPos)){
                if(prodTypeFlag==parseREP){
                    me int: MAX_ITEMS  <- backProd.items[2]
                    if((backSRecSeqPos < MAX_ITEMS or MAX_ITEMS==0) and backProd.items[0] == SRec.productionID ){
    //                    print(" ADVANCING REP: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else{print(" TOO MANY REPS\n")}
                } else if(prodTypeFlag==parseSEQ){
                    if(backSRecSeqPos < backProd.items.size() and backProd.items[backSRecSeqPos] == SRec.productionID){
     //                   print(" ADVANCING SEQ: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else {print(" SEQ is NOT ADVANCING  \n")}
                } else if(prodTypeFlag==parseALT){
                    if(backSRecSeqPos == 0){
                        withEach backAltProdID in backProd.items {
                            if(backAltProdID==SRec.productionID){
    //                            print(" ADVANCING ALT: ")
                                addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                                break()
                            } //else {if(backAltProdID_key) {print("                                  ")} print(" SKIP ALT\n")}
                        }
                    }
                } //else {print(" NOTHING for prodType ", prodTypeFlag, "\n")}
            } //else {print("Triggering Item... Skipping.\n")}
        }
    }

    //////////////////////////////////////

    void: complete(our stateRec: SRec, me int: crntPos) <- {
    //    print('        COMPLETING: check items at origin %i`SRec->originPos`... \n')
        registerCompletion(SRec)
        their stateSets: SSet  <- SSets[SRec.originPos]
        withEach backSRec in SSet.stateRecs {
            their production: backProd <- grammar[backSRec.productionID]
    //        print('                Checking Item #%i`backSRec_key`: ')
            me int: prodTypeFlag <- backProd.prodType
            me int: backSRecSeqPos <- backSRec.SeqPosition
            if(!(crntPos==SRec.originPos and backSRec.productionID==SRec.productionID and backSRec.SeqPosition==SRec.SeqPosition and backSRec.originPos==SRec.originPos)){
                if(prodTypeFlag==parseREP){
                    me int: MAX_ITEMS  <- backProd.items[2]
                    if((backSRecSeqPos < MAX_ITEMS or MAX_ITEMS==0) and backProd.items[0] == SRec.productionID ){
    //                    print(" ADVANCING REP: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    } //else{print(" TOO MANY REPS\n")}
                } else if(prodTypeFlag==parseSEQ){
                    if(backSRecSeqPos < backProd.items.size() and backProd.items[backSRecSeqPos] == SRec.productionID){
     //                   print(" ADVANCING SEQ: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else {print(" SEQ is NOT ADVANCING  \n")}
                } else if(prodTypeFlag==parseALT){
                    if(backSRecSeqPos == 0){
                        withEach backAltProdID in backProd.items {
                            if(backAltProdID==SRec.productionID){
     //                           print(" ADVANCING ALT: ")
                                addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                                break()
                            } //else {if(backAltProdID_key) {print("                                  ")} print(" SKIP ALT\n")}
                        }
                    }
                }// else {print(" NOTHING for prodType ", prodTypeFlag, "\n")}
            } //else {print("Triggering Item... Skipping.\n")}
        }
    //    print("\n")
    }

    me bool: ruleIsDone(me bool: isTerminal, me int: seqPos, me int: ProdType, me int: numItems)<-{
        if(isTerminal and seqPos==1) {return(true)}
        if(!isTerminal){
            if(ProdType==parseSEQ and seqPos==numItems) {return(true)}
            if(ProdType==parseALT and seqPos==1) {return(true)}
        }
        return(false)
    }

    void: doParse() <- {
        parseFound <- false
        withEach crntPos in RANGE(0 .. SSets.size()) {
            their stateSets: SSet <- SSets[crntPos]

    //        print('\n\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   PROCESSING SLOT: %i`crntPos` "%s`ch.data()`"   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')
            resetCompletions(crntPos)
            withEach SRec in SSet.stateRecs {
                their production: prod <- grammar[SRec.productionID]
                me int: ProdType <- prod.prodType
                me bool : isTerminal <- prod.isTerm != 0
                me int: seqPos <- SRec.SeqPosition
     //           print('    PROCESSING-RECORD #%i`SRec_key`:')
    //            SRec.printSREC(self)
                if(ruleIsDone(isTerminal, seqPos, ProdType, prod.items.size())){             // COMPLETER
                    complete(SRec, crntPos)  // Notate that SEQ is finished, actually add parent's follower.
                }else{
                    if(isTerminal){       // SCANNER
                        // print("SCANNING for matching termiinal...\n") // Scanning means Testing for a Matching terminal
                        me int: len <- textMatches(SRec.productionID, crntPos)
                        if(len>=0 and crntPos+len<SSets.size()){ // if match succeeded
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos, SRec, NULL)  // Notate that terminal is finished, mark for adding parent's follower.
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        //print("NON_TERMINAL \n")
                        if(ProdType == parseREP){
                            me int: MIN_ITEMS <- prod.items[1]
                            me int: MAX_ITEMS <- prod.items[2]
                            me bool: must_be   <- seqPos < MIN_ITEMS
                            me bool: cannot_be <- seqPos > MAX_ITEMS and (MAX_ITEMS!=0)
                            if(!must_be){
                                complete(SRec, crntPos)
     //                           print("         REP (TENT): ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, NULL) // Tentative
                            } else {if(!cannot_be){
     //                           print("         REP: ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, NULL)
                            }}
                        } else { // Not a REP
    //                        print("         SEQ|ALT: ")
                            addProductionToStateSet(crntPos, prod.items[seqPos], 0, crntPos, SRec, NULL)  // Add a cause SEQ with cursor at the very beginning. (0)
                        }
                    }
                }
            }
        }
  //      print("\n\n#####################################\n")
  //      dump()
    }

    void: countLinesToCharPos(me int: charPos) <- {
        errLineNum <- 1
        me int: lastLinePos <- 0
        withEach C in RANGE(0..charPos){
            me char: ch <- textToParse[C]
            if(ch == "\n"){
                errLineNum <- errLineNum+1
                lastLinePos <- C
            }
        }
        errCharPos <- charPos-lastLinePos+1
    }

    me bool: doesParseHaveError() <- {
  //      logMesg("\n\nChecking for Parse Errors...\n")
        errorMesg <- ""
        me int: lastSSetIDX <- SSets.size()
        me int: lastPosWithItems <- 0
        withEach ssetIDX in Backward RANGE(0 .. lastSSetIDX){
            their stateSets: SSet <- SSets[ssetIDX]
            me int: numItems <- SSet.stateRecs.size()
            if(numItems>0 and lastPosWithItems==0){lastPosWithItems <- ssetIDX}
         //   print("Position ", ssetIDX, " has ", numItems, "items.\n")
        }
  //      print("lastPosWithItems:", lastPosWithItems, "\n")

        their stateSets: lastSSet <- SSets[lastPosWithItems]

        me int: lastSRecIDX <- lastSSet.stateRecs.size()-1
        our stateRec: lastSRec // <- lastSSet.stateRecs[lastSRecIDX]
        their production: prod
        me int: ProdType <- 0
        me int: isTerminal<- 0
        me int: seqPos<- 0
      //  lastSRec.printSREC(self) print("\n----\n")

        withEach SRec in lastSSet.stateRecs {
            lastSRec <- SRec
            prod <- grammar[SRec.productionID]
            ProdType <- prod.prodType
            isTerminal <- prod.isTerm
            seqPos <- SRec.SeqPosition
            if (SRec.productionID==startProduction and SRec.originPos==0 and ((lastPosWithItems+1)==lastSSetIDX) and seqPos==prod.items.size()){
 //               print("Passed\n")  // !!!!!!!!!!!!!!!!!!! This tells when the parse passes.
                return(false)
            }
            //SRec.printSREC(self)
        }

        //lastSRec.printSREC(self) print("\n----\n", seqPos)
        if(isTerminal!=0){
            if(seqPos==0){
                errorMesg <- "Expected '" + prod.constStr + "'"
                countLinesToCharPos(lastPosWithItems)
            }
        }

        if(errorMesg=="" and (lastPosWithItems+1)!=lastSSetIDX){
            errorMesg<-'Parse failed for unknown reason.'
        }
        if(errorMesg=="") {return(false)}
        else {return(true)}
    }

    me int: choosePedigreeToFollow(me int: prodID, me pedigree[their list]: peds) <- {
        return(0)
    }

    our stateRec: resolve(our stateRec: LastTopLevelItem, me string: indent) <- {
        if(LastTopLevelItem == NULL){print("\nStateRecPtr is null.\n\n") exit(1)}
        our stateRec: crntRec <- LastTopLevelItem
        me int: seqPos <- crntRec.SeqPosition
        me int: prodID <- crntRec.productionID
        their production: Prod <- grammar[prodID]
 //       print(indent+'grammar[%i`prodID`] = ')  crntRec.printSREC(self)  print("\n", indent, "\n")
        if(Prod.isTerm){
        } else if(seqPos>0){
            withEach subItem in Backward RANGE(0 .. seqPos) {
//                print(indent, "//-item #", subItem, ": \n")
                me int: pedToFollow <- choosePedigreeToFollow(prodID, crntRec.pedigrees)
                me pedigree: ped <- crntRec.pedigrees[pedToFollow]
                crntRec.child <- resolve(ped.cause, indent+"|    ")
                ped.pred.next <- crntRec
                crntRec <- ped.pred
 //               print(indent, "############# ") crntRec.print(self) print("\n")
            }
        }
 //       if(indent==""){  print("\nRESOLVED\n\n") }
        return(crntRec)
    }

    void: docPos(me int: indent, our stateRec: SRec, me string: tag) <- {
        withEach i in RANGE(0 .. indent){ print("|    ")}
        if(SRec){
            SRec.printSREC(self)
        } else {print(" NULL ")}
        print("  \t", tag, "\n")
    }

    void: displayParse(our stateRec: SRec, me string: indent) <- {
        their production: prod <- grammar[SRec.productionID]
        if(prod.isTerm){
            print(indent, "'")
            withEach i in RANGE(SRec.originPos .. SRec.crntPos){
                print(textToParse[i])
            }
            print("'\n")
        } else {
           // print(indent) SRec.printSREC(self) print("\n")
            if(SRec.child){
                displayParse(SRec.child, indent+"   | ")
            }
            if(SRec.next){
                displayParse(SRec.next, indent)
            }
        }
    }

}
    """
    code=code.replace('#CONST_CODE_HERE', ConstList, 1)
    code=code.replace('#GRAMMAR_CODE_HERE', RuleList, 1)
    return code

def writePositionalFetch(classes, tags, field):
    fname=field['fieldName']
    fieldType=str(progSpec.getFieldType(field))
    S="""
    me fetchResult: fetch_%s() <- {
        if(%s_hasVal) {return (fetchOK)}
        }
"""% (fname, fname)
    return S




    #print 'FIELD:', fname, field['owner'], '"'+fieldType+'"'
    if(field['owner']=='const' and fieldType=='string'):
        S+='    %s_hasLen <- true \n    %s_span.len <- '% (fname, fname) + str(len(field['value']))
    S+="        if(! %s_hasPos){pos <- pred.pos+pred.len}\n" % (fname)
    S+="        if( %s_hasPos){\n" % (fname)
    # Scoop Data
    S+=' FieldTYpe("' + fieldType +'")\n'
    if progSpec.isStruct(fieldType):
        #print " Call stuct's fetch()"
        pass
    #elif fieldType=='':
    # Set and propogate length
    S+="        }\n"
    S+='    }'

    return S

def writePositionalSet(field):
    return "    // Positional Set() TBD\n";

def writeContextualGet(field):
    return "    // Contextual Get() TBD\n";

def writeContextualSet(field):
    return "    // Contextual Set() TBD\n";


def appendRule(ruleName, termOrNot, pFlags, prodData):
    global rules
    global constDefs
    global ruleSet
    # If rule already exists, return the name rather than recreate it
    # is there a rule with the same term, flags, and prodData? (Only care about term+parseSEQ+data)
    if (ruleName in ruleSet):
        ruleSet[ruleName]+=1
    else:
        thisIDX=len(rules)
        if not isinstance(ruleName, str):
            ruleName="rule"+str(thisIDX)
        constDefs.append([ruleName, str(thisIDX)])
        #print "PRODDATA:", prodData
        if isinstance(prodData, list):
            prodData='['+(', '.join(map(str,prodData))) + ']'
        rules.append([ruleName, termOrNot, pFlags, prodData])
        ruleSet[ruleName]=0
    return ruleName


definedRules={}

def populateBaseRules():
    definedRulePairs=[['{','lBrace'],  ['}','rBrace'], ['(','lParen'],  [')','rParen'],  ['[','lBrckt'],  [']','rBrckt'],  [' ','space'],  [',','comma'],
            ['!','bang'],  ['.','period'],  ['/','slash'],  ['?','question'],  [':','colon'],  ['`','quoteBack'],  ["'",'quote1'],  [r'\"','quote2'],
            ['-','minus'],  ['+','plus'],  ['=','equals'],  ['*','star'], ['<','lessThan'],  ['>','grtrThan'],  ['@','atSign'], ['#','hashMark'],  ['$','dollarSign'],
            ['%','percent'],  ['^','carot'], ['~','tilde'], ['_','underscore'],  ['|','bar'], [r'\\','backSlash'],  [';','semiColon'] ]

    for pair in definedRulePairs:
        appendRule(pair[1], "term", "parseSEQ",  pair[0])
        definedRules[pair[0]]=pair[1]

    # Define common string formats
    appendRule('alphaSeq',    'term', 'parseAUTO', "an alphabetic string")
    appendRule('uintSeq',     'term', 'parseAUTO', 'an unsigned integer')
    appendRule('intSeq',      'term', 'parseAUTO', 'an integer')
    appendRule('RdxSeq',      'term', 'parseAUTO', 'a number')
    appendRule('alphaNumSeq', 'term', 'parseAUTO', "an alpha-numeric string")
    appendRule('ws',          'term', 'parseAUTO', 'white space')
    appendRule('quotedStr',   'term', 'parseAUTO', "a quoted string with single or double quotes and escapes")
    appendRule('quotedStr1',  'term', 'parseAUTO', "a single quoted string with escapes")
    appendRule('quotedStr2',  'term', 'parseAUTO', "a double quoted string with escapes")
    appendRule('HexNum_str',      'term', 'parseAUTO', "a hexidecimal number")
    appendRule('BinNum_str',      'term', 'parseAUTO', "a hexidecimal number")
    appendRule('BigInt',      'term', 'parseAUTO', "an integer")
    appendRule('CID',         'term', 'parseAUTO', 'a C-like identifier')
    appendRule('UniID',       'term', 'parseAUTO', 'a unicode identifier for the current locale')
    appendRule('printables',  'term', 'parseAUTO', "a seqence of printable chars")
    appendRule('toEOL',       'term', 'parseAUTO', "to read chars to End Of Line, including EOL.")
    # TODO: delimited List, keyWord



nextParseNameID=0 # Global used to uniquify sub-seqs and sub-alts in a struct parse. E.g.: ruleName: parse_myStruct_sub1
def fetchOrWriteTerminalParseRule(modelName, field, logLvl):
    global nextParseNameID
    #print "FIELD_IN:", modelName, field
    fieldName='N/A'
    fieldValue=''
    if 'value' in field: fieldValue =field['value']
    typeSpec   = field['typeSpec']
    fieldType  = progSpec.getFieldType(typeSpec)
    fieldOwner = typeSpec['owner']
    if 'fieldName' in field: fieldName  =field['fieldName']
    cdlog(logLvl, "WRITING PARSE RULE for: {}.{}".format(modelName, fieldName))
    #print "WRITE PARSE RULE:", modelName, fieldName

    nameIn=None
    nameOut=None
    if fieldOwner=='const':
        if fieldType=='string':
            if fieldValue in definedRules: nameOut=definedRules[fieldValue]
            else: nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='uint':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:3]=='int':    nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:6]=='double': nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        else:
            print("Unusable const type in fetchOrWriteTerminalParseRule():", fieldType); exit(2);

    elif fieldOwner=='me' or  fieldOwner=='their' or  fieldOwner=='our':
        if fieldType=='string':        nameOut='quotedStr'
        elif fieldType[0:4]=='uint':   nameOut='uintSeq'
        elif fieldType[0:3]=='int':    nameOut='intSeq'
        elif fieldType[0:6]=='double': nameOut='RdxSeq'
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif progSpec.isStruct(fieldType):
            objName=fieldType[0]
            if objName=='ws' or objName=='quotedStr' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq' or progSpec.typeIsInteger(objName):
                nameOut=objName
            else:
                if objName=='[' or objName=='{': # This is an ALT or SEQ sub structure
                    print("ERROR: These should be handled in writeNonTermParseRule().\n")
                    exit(1)
                else: nameOut=objName+'_str'
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print("Unusable type in fetchOrWriteTerminalParseRule():", fieldType); exit(2);
    else: print("Pointer types not yet handled in fetchOrWriteTerminalParseRule():", fieldType); exit(2);

    if progSpec.isAContainer(typeSpec):
        global rules
        containerSpec = progSpec.getContainerSpec(typeSpec)
        idxType=''
        if 'indexType' in containerSpec:
            idxType=containerSpec['indexType']
        if(isinstance(containerSpec['datastructID'], str)):
            datastructID = containerSpec['datastructID']
        else:   # it's a parseResult
            datastructID = containerSpec['datastructID'][0]
        if idxType[0:4]=='uint': pass
        if(datastructID=='list'):
            nameOut=appendRule(nameOut+'_REP', "nonterm", "parseREP", [nameOut, 0, 0])
        elif datastructID=='opt':
            nameOut=appendRule(nameOut+'_OPT', "nonterm", "parseREP", [nameOut, 0, 1])
            #print("NAMEOUT:", nameOut)
    field['parseRule']=nameOut
    return nameOut

def writeNonTermParseRule(classes, tags, modelName, fields, SeqOrAlt, nameSuffix, logLvl):
    global nextParseNameID
    nameIn=modelName+nameSuffix

    # Allocate or fetch a rule identifier for each '>' field.

    partIndexes=[]
    for field in fields:
        fname=field['fieldName']
        if fname==None: fname=''
        else: fname='_'+fname
        typeSpec   =field['typeSpec']
        if(field['isNext']==True): # means in the parse there was a '>' symbol, a sequence seperator
            firstItm=progSpec.getFieldType(field['typeSpec'])[0]
            if firstItm=='[' or firstItm=='{': # Handle an ALT or SEQ sub structure
                cdlog(logLvl, "NonTERM: {} = {}".format(fname, firstItm))
                nextParseNameID+=1
                if firstItm=='[':
                    innerSeqOrAlt='parseALT'
                    newNameSuffix = nameSuffix+fname+'_ALT'+str(nextParseNameID)
                else:
                    innerSeqOrAlt='parseSEQ'
                    newNameSuffix = nameSuffix+fname+'_SEQ'+str(nextParseNameID)
                innerFields=field['innerDefs']
                ruleIdxStr = writeNonTermParseRule(classes, tags, modelName, innerFields, innerSeqOrAlt, newNameSuffix, logLvl+1)
                field['parseRule']=ruleIdxStr


                if progSpec.isAContainer(typeSpec):
                    # anything with [] is a container: lists and optionals
                    global rules
                    containerSpec = progSpec.getContainerSpec(typeSpec)
                    idxType=''
                    if 'indexType' in containerSpec:
                        idxType=containerSpec['indexType']
                    if(isinstance(containerSpec['datastructID'], str)):
                        datastructID = containerSpec['datastructID']
                    else:   # it's a parseResult
                        datastructID = containerSpec['datastructID'][0]
                    if idxType[0:4]=='uint': pass
                    if(datastructID=='list'):
                        ruleIdxStr=appendRule(ruleIdxStr+'_REP', "nonterm", "parseREP", [ruleIdxStr, 0, 0])
                    elif datastructID=='opt':
                        ruleIdxStr=appendRule(ruleIdxStr+'_OPT', "nonterm", "parseREP", [ruleIdxStr, 0, 1])
            else:
                ruleIdxStr = fetchOrWriteTerminalParseRule(modelName, field, logLvl)

            partIndexes.append(ruleIdxStr)
        else: pass; # These fields probably have corresponding cofactuals

    nameOut=appendRule(nameIn, "nonterm", SeqOrAlt, partIndexes)
    return nameOut

#######################################################   E x t r a c t i o n   F u n c t i o n s

def getFunctionName(fromName, toName):
    if len(fromName)>=5 and fromName[-5:-3]=='::': fromName=fromName[:-5]
    if len(toName)>=5 and toName[-5:-3]=='::': toName=toName[:-5]
    S='Extract_'+fromName.replace('::', '_')+'_to_'+toName.replace('::', '_')
    return S

def fetchMemVersion(classes, objName):
    if objName=='[' or objName=='{': return [None, None]
    memObj = progSpec.findSpecOf(classes[0], objName, 'struct')
    if memObj==None: return [None, None]
    return [memObj, objName]


def Write_ALT_Extracter(classes, parentStructName, fields, VarTagBase, VarTagSuffix, VarName, indent, level, logLvl):
    # Structname should be the name of the structure being parsed. It will be converted to the mem version to get 'to' fields.
    # Fields is the list of alternates.
    # VarTag is a string used to create local variables.
    # VarName is the LVAL variable name.
    global  globalFieldCount
    cdlog(logLvl, "WRITING code to extract one of {} from parse tree...".format(parentStructName))
    InnerMemObjFields = []
    progSpec.populateCallableStructFields(InnerMemObjFields, classes, parentStructName)
    if parentStructName.find('::') != -1: cdErr("TODO: Make string parsing work on derived classes. Probably just select the correct fields for the destination struct.")
    S=""
    # Code to fetch the ruleIDX of this ALT. If the parse was terminal (i.e., 'const'), it will be at a different place.
    if(level==-1):
        level=1
        VarTag='SRec1'
        VarTagSuffix='0'
    else:
        globalFieldCount+=1
        VarTag=VarTagBase+str(level)
        VarTagSuffix=str(level-1)+'.child.next'+VarTagSuffix

    indent2 = indent+'    '
    S+='\n'+indent+'{\n'
    S+='\n'+indent2+'our stateRec: '+VarTag+' <- '+VarTagBase+VarTagSuffix+'\n'
    loopVarName = "ruleIDX"+str(globalFieldCount)
    S+=indent2+'me int: '+loopVarName+' <- '+VarTag+'.child.productionID\n'

    #print "RULEIDX:", indent, parentStructName, VarName
    if VarName!='memStruct':
        S+=indent2 + 'me string: '+VarName+'\n'
    count=0
    S+= indent2+"switch("+loopVarName+"){\n"
    for altField in fields:
        if(altField['isNext']!=True): continue; # This field isn't in the parse stream.
        cdlog(logLvl+1, "ALT: {}".format(altField['parseRule']))
        if not 'parseRule' in altField: print("Error: Is syntax missing a '>'?"); exit(2);
        S+=indent2+"    case " + altField['parseRule'] + ":{\n"
        coFactualCode=''
        if 'coFactuals' in altField:
            #Extract field and cofactsList
            for coFact in altField['coFactuals']:
                coFactualCode+= indent2 +'        ' + VarName + '.' + coFact[0] + ' <- ' + coFact[2] + "\n"
                cdlog(logLvl+2, "Cofactual: "+coFactualCode)
        S+=Write_fieldExtracter(classes, parentStructName, altField, InnerMemObjFields, VarTagBase, VarName, False, indent2+'        ', level, logLvl+1)
        S+=coFactualCode
        S+=indent2+"    }\n"
        count+=1
    S+=indent2+"}"
    S+=indent+"}"
    return S


def CodeRValExpr(toFieldType, VarTag):
    if   toFieldType=='string':          CODE_RVAL='makeStr('+VarTag+'.child'+')'+"\n"
    elif toFieldType[0:4]=='uint':       CODE_RVAL='makeInt('+VarTag+'.child'+')'+"\n"
    elif toFieldType[0:3]=='int':        CODE_RVAL='makeInt('+VarTag+'.child'+')'+"\n"
    elif toFieldType[0:6]=='double':     CODE_RVAL='makeDblFromStr('+VarTag+'.child'+')'+"\n"
    elif toFieldType[0:4]=='char':       CODE_RVAL="crntStr[0]"+"\n"
    elif toFieldType[0:4]=='bool':       CODE_RVAL='crntStr=="true"'+"\n"
    elif toFieldType[0:4]=='flag':       CODE_RVAL=''
    else: print("TOFIELDTYPE:", toFieldType); exit(2);
    return CODE_RVAL


def Write_fieldExtracter(classes, ToStructName, field, memObjFields, VarTagBase, VarName, advancePtr, indent, level, logLvl):
    debugTmp=False # Erase this line
    VarTag=VarTagBase+str(level)
    ###################   G a t h e r   N e e d e d   I n f o r m a t i o n
    global  globalFieldCount
    global  globalTempVarIdx
    S=''
    fieldName  = field['fieldName']
    fieldIsNext= field['isNext']
    fieldValue = field['value']
    typeSpec   = field['typeSpec']
    fieldType  = progSpec.getFieldType(typeSpec)
    fieldOwner =typeSpec['owner']
    fromIsEmbeddedAlt = (not isinstance(fieldType, str) and fieldType[0]=='[')
    fromIsEmbeddedSeq = (not isinstance(fieldType, str) and fieldType[0]=='{')
    fromIsEmbedded    = fromIsEmbeddedAlt or fromIsEmbeddedSeq

    if(fieldIsNext!=True): return '' # This field isn't in the parse stream.

    [memObj, memVersionName]=fetchMemVersion(classes, ToStructName)

    toField = progSpec.fetchFieldByName(memObjFields, fieldName)
    if(toField==None):
        #print "   TOFIELD == None", fieldName
        # Even tho there is no LVAL, we need to move the cursor. Also, there could be a co-factual.
        toFieldType = progSpec.TypeSpecsMinimumBaseType(classes, typeSpec)
        toTypeSpec=typeSpec
        toFieldOwner="me"
    else:
        toTypeSpec   = toField['typeSpec']
        toFieldType  = progSpec.getFieldType(toTypeSpec)
        toFieldOwner = progSpec.getInnerContainerOwner(toTypeSpec)

        if debugTmp:
            print('        toFieldType:', toFieldType)

    LHS_IsPointer=progSpec.typeIsPointer(toTypeSpec)

   # print "        CONVERTING:", fieldName, str(toFieldType)[:100]+'... ', str(typeSpec)[:100]+'... '
   # print "            TOFieldTYPE1:", str(toField)[:100]
   # print "            TOFieldTYPE :", toFieldOwner, toFieldType
   # print "       fieldValue:",ToStructName, fieldType, fieldValue
    cdlog(logLvl, "FIELD {}: '{}'".format(fieldName, str(fieldValue)))

    fields=[]
    fromIsStruct=progSpec.isStruct(fieldType)
    toIsStruct=progSpec.isStruct(toFieldType)
    ToIsEmbedded = toIsStruct and (toFieldType[0]=='[' or toFieldType[0]=='{')
    [fromIsALT, fields] = progSpec.isAltStruct(classes, fieldType)
    fromIsOPT =False
    fromIsList=False
    toIsList  =False
    if progSpec.isAContainer(typeSpec):
        datastructID = progSpec.getDatastructID(typeSpec)
        if datastructID=='opt': fromIsOPT=True;
        else: fromIsList=True

    if progSpec.isAContainer(toTypeSpec):
        if datastructID != 'opt': toIsList=True

    if debugTmp:
        print('        fromIsOPT:', fromIsOPT)
        print('        fromIsList:', fromIsList)
        print('        toIsList:', toIsList)
        print('        fromIsStruct:', fromIsStruct)
        print('        toIsStruct:', toIsStruct)
        print('        fieldType:', fieldType)
        print('        ToIsEmbedded:', ToIsEmbedded)
        print('        ToStructName:', ToStructName)
        print('        memVersionName:', memVersionName, "\n")
    ###################   W r i t e   L V A L   R e f e r e n c e
    finalCodeStr=''
    CodeLVAR_Alloc=''
    CODE_LVAR_v2=''
    if VarName=='' or VarName=='memStruct':  # Default to the target argument name
        #if VarName=='': print "        VARNAME was ''; FIELDNAME:", fieldName
        VarName='memStruct'
        if(fieldName==None): # Field hasn't a name so in memory it's a cofactual or this is a parser marker.
            globalFieldCount+=1
            # We need two versions in case this is set in a function instead of assignment
            CODE_LVAR_v2 = 'S'+str(globalFieldCount)
            CodeLVAR_Alloc='    me string: '+CODE_LVAR_v2
            CODE_LVAR = CodeLVAR_Alloc
            if debugTmp: print('        CODE_LVARS:', CODE_LVAR)
        else:
            CODE_LVAR = VarName+'.'+fieldName
            if fieldName=='inf': CODE_LVAR = VarName
            CODE_LVAR_v2 = CODE_LVAR
    else:
        CODE_LVAR = VarName
        CODE_LVAR_v2 = CODE_LVAR

    ###################   W r i t e   R V A L   C o d e
    CODE_RVAL=''
    objName=''
    humanIDType= VarTag+' ('+str(fieldName)+' / '+str(fieldValue) + ' / '+str(fieldType)[:40] +')'
    humanIDType=humanIDType.replace('"', "'")
    #print humanIDType

    if advancePtr:
        S+=indent+VarTag+' <- getNextStateRec('+VarTag+')\n'
        # UNCOMMENT FOR DEGUG: S+='    docPos('+str(level)+', '+VarTag+', "Get Next in SEQ for: '+humanIDType+'")\n'


    if fieldOwner=='const'and (toField == None):
        #print'CONSTFIELDVALUE("'+fieldValue+'")\n'
        finalCodeStr += indent + 'tmpStr'+' <- makeStr('+VarTag+"<LVL_SUFFIX>"+'.child)\n'

    else:
        if toIsStruct:
            if debugTmp: print('        toFieldType:', toFieldType)
            if not ToIsEmbedded:
                objName=toFieldType[0]
                if  progSpec.typeIsInteger(objName):
                    strFieldType = fieldType[0]
                    if(strFieldType == "BigInt"):
                        CODE_RVAL='makeStr('+VarTag+'.child'+')'
                    elif(strFieldType == "HexNum"):
                        CODE_RVAL='makeHexInt('+VarTag+'.child'+')'
                    elif(strFieldType == "BinNum"):
                        CODE_RVAL='makeBinInt('+VarTag+'.child'+')'
                    else:
                        CODE_RVAL='makeStr('+VarTag+'.child'+')'
                    toIsStruct=False; # false because it is really a base type.
                elif objName=='ws' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq':
                    CODE_RVAL='makeStr('+VarTag+'.child'+')'
                    toIsStruct=False; # false because it is really a base type.
                else:
                    #print "toObjName:", objName, memVersionName, fieldName
                    [toMemObj, toMemVersionName]=fetchMemVersion(classes, objName)
                    if toMemVersionName==None:
                        # make alternate finalCodeStr. Also, write the extractor that extracts toStruct fields to memVersion of this
                        childStr = ".child"
                        if fromIsOPT:
                            childStr += ".next"
                        finalCodeStr=(indent + CodeLVAR_Alloc + '\n' +indent+'    '+getFunctionName(fieldType[0], memVersionName)+'('+VarTag+"<LVL_SUFFIX>"+childStr+', memStruct)\n')
                        objSpec = progSpec.findSpecOf(classes[0], objName, 'string')
                        ToFields=objSpec['fields']
                        FromStructName=objName
                        Write_Extracter(classes, ToStructName, FromStructName, logLvl+1)
                    else:
                        fromFieldTypeCID = fieldType[0].replace('::', '_')
                        toFieldTypeCID = toMemVersionName.replace('::', '_')
                        #print "FUNC:", getFunctionName(fromFieldTypeCID, toFieldTypeCID)
                        if fromFieldTypeCID != toFieldTypeCID:
                            Write_Extracter(classes, toFieldTypeCID, fromFieldTypeCID, logLvl+1)
                        finalCodeStr=indent + CodeLVAR_Alloc + '\n' +indent+'    '+getFunctionName(fromFieldTypeCID, toFieldTypeCID)+'('+VarTag+"<LVL_SUFFIX>"+'.child, '+CODE_LVAR_v2+')\n'
            else: pass

        else:
            CODE_RVAL = CodeRValExpr(toFieldType, VarTag)


    #print "CODE_RVAL:", CODE_RVAL

    ###################   H a n d l e   o p t i o n a l   a n d   r e p e t i t i o n   a n d   a s s i g n m e n t   c a s e s
    gatherFieldCode=''
    if fromIsList and toIsList:
        CODE_RVAL='tmpVar'
        globalFieldCount +=1
        childRecName='SRec' + str(globalFieldCount)
        gatherFieldCode+='\n'+indent+'\nour stateRec: '+childRecName+' <- '+VarTag+'.child.next'
        gatherFieldCode+='\n'+indent+'while('+childRecName+'){\n'
        if fromIsALT:
          #  print "ALT-#1"
            gatherFieldCode+=Write_ALT_Extracter(classes, fieldType[0], fields, childRecName, '', 'tmpVar', indent+'    ', level)

        elif fromIsStruct and toIsStruct:
            gatherFieldCode+='\n'+indent+toFieldOwner+' '+progSpec.baseStructName(toFieldType[0])+': tmpVar'
            if toFieldOwner!='me':
                gatherFieldCode+='\n'+indent+'Allocate('+CODE_RVAL+')'
            #print "##### FUNCT:", getFunctionName(fieldType[0], fieldType[0])
            gatherFieldCode+='\n'+indent+getFunctionName(fieldType[0], toFieldType[0])+'('+childRecName+'.child, tmpVar)\n'

        else:
            CODE_RVAL = CodeRValExpr(toFieldType, childRecName, '') # TODO: one too many arguments
            #CODE_RVAL=childRecName+'.child'

        # Now code to push the chosen alternative into the data field# This is a LIST, not an OPT:
        gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'

        gatherFieldCode+=indent+'    '+childRecName+' <- getNextStateRec('+childRecName+')\n'
        # UNCOMMENT FOR DEGUG: S+= '    docPos('+str(level)+', '+VarTag+', "Get Next in LIST for: '+humanIDType+'")\n'


        gatherFieldCode+='\n'+indent+'}\n'
        if(fromIsOPT):
            print("Handle when the optional item is a list.");
            exit(2)
    else:
        if toIsList: print("Error: parsing a non-list to a list is not supported.\n"); exit(1);
        levelSuffix=''
        assignerCode=''
        oldIndent=indent
        if (fromIsOPT):
            setTrueCode=''
            assignerCode+='\n'+indent+'if('+VarTag+'.child.next' +' == NULL){'
            if toFieldOwner=='me':
                if debugTmp: print('        toFieldOwner:', toFieldOwner)
                ## if fieldName==None and a model of fromFieldType has no cooresponding model But we are in EXTRACT_ mode:
                        ## Make a special form of Extract_fromFieldType_to_ToFieldType()
                        ## Call that function instead of the one in Code_LVAR
                # First, create a new flag field
                if fieldName==None:
                    fieldName="TEMP"+str(globalTempVarIdx)
                    globalTempVarIdx += globalTempVarIdx
                newFieldsName=fieldName   #'has_'+fieldName
                fieldDef=progSpec.packField(ToStructName, False, 'me', 'flag', None, None, newFieldsName, None, None, None, False)
                progSpec.addField(classes[0], memVersionName, 'struct', fieldDef)

                # Second, generate the code to set the flag
                assignerCode+='\n'+indent+'    '+VarName+'.'+newFieldsName+' <- false'
                setTrueCode += VarName+'.'+newFieldsName+' <- true'
            elif LHS_IsPointer: # If owner is my, our or their
                assignerCode+='\n'+indent+'    '+CODE_LVAR+' <- NULL'
            else:
                print("ERROR: OPTional fields must not be '"+toFieldOwner+"'.\n")
                exit(1)
            assignerCode+='\n'+indent+'} else {\n'
            levelSuffix='.child.next'
            indent+='    '
            assignerCode+=indent+setTrueCode+'\n'


        if fromIsALT or fromIsEmbeddedAlt:
            if(fromIsEmbeddedAlt):
               # print "ALT-#2"
                assignerCode+=Write_ALT_Extracter(classes, ToStructName, field['innerDefs'], VarTagBase, levelSuffix, VarName, indent+'    ', level+1, logLvl+1)
            else:
              #  print "ALT-#3"
                assignerCode+=Write_ALT_Extracter(classes, fieldType[0], fields, VarTagBase, levelSuffix, VarName+'X', indent+'    ', level, logLvl+1)
                assignerCode+=indent+CODE_LVAR+' <- '+(VarName+'X')+"\n"
        elif fromIsEmbeddedSeq:
            globalFieldCount +=1
            childRecNameBase='childSRec' + str(globalFieldCount)
            childRecName=childRecNameBase+str(level)
            assignerCode+='\n'+indent+'our stateRec: '+childRecName+' <- '+VarTag+levelSuffix+'.child\n'
            for innerField in field['innerDefs']:
                assignerCode+=Write_fieldExtracter(classes, ToStructName, innerField, memObjFields, childRecNameBase, '', True, '    ', level, logLvl+1)
        elif fromIsStruct and toIsStruct:
            assignerCode+=finalCodeStr.replace("<LVL_SUFFIX>", levelSuffix);
            if debugTmp: print('        assignerCode:', assignerCode)
        else:
           # if toFieldOwner == 'const': print "Error: Attempt to extract a parse to const field.\n"; exit(1);
            if CODE_RVAL!="":
                if LHS_IsPointer:
                    assignerCode+='        '+CODE_LVAR+' <deep- '+CODE_RVAL+"\n"
                else: assignerCode+='        '+CODE_LVAR+' <- '+CODE_RVAL+"\n"
            elif finalCodeStr!="": assignerCode+=finalCodeStr.replace("<LVL_SUFFIX>", levelSuffix);

        if (fromIsOPT):
            indent=oldIndent
            assignerCode += indent+'}\n'
            #print '######################\n'+assignerCode, memVersionName, '\n'
           # exit(2)
        gatherFieldCode = assignerCode
    #print "##########################\n",S,"\n#####################################\n"
    if LHS_IsPointer: # LVAL is a pointer and should be allocated or cleared.
        S+= indent + 'AllocateOrClear(' +CODE_LVAR +')\n'

    S+=gatherFieldCode
    #print "ASSIGN_CODE", S
 #   if debugTmp: exit(2)
    return S

extracterFunctionAccumulator = ""
alreadyWrittenFunctions={}

def Write_structExtracter(classes, ToStructName, FromStructName, fields, nameForFunc, logLvl):
    memObjFields=[]
    progSpec.populateCallableStructFields(memObjFields, classes, ToStructName)
    if memObjFields==None: cdErr("struct {} is not defined".format(ToStructName.replace('str','mem')))
    S='    me string: tmpStr\n'
    for field in fields: # Extract all the fields in the string version.
        S+=Write_fieldExtracter(classes, ToStructName, field, memObjFields, 'SRec', '', True, '    ', 0, logLvl+1)
    if  ToStructName== FromStructName and progSpec.doesClassContainFunc(classes, ToStructName, 'postParseProcessing'):
        S += 'memStruct.postParseProcessing()\n'
    return S

def Write_Extracter(classes, ToStructName, FromStructName, logLvl):
    global extracterFunctionAccumulator
    global alreadyWrittenFunctions
    nameForFunc=getFunctionName(FromStructName, ToStructName)
    cdlog(logLvl, "WRITING function {}() to extract struct {} from parse tree: stage 1...".format(nameForFunc, ToStructName))
    if nameForFunc in alreadyWrittenFunctions: return
    alreadyWrittenFunctions[nameForFunc]=True
    S=''
    ObjectDef = progSpec.findSpecOf(classes[0], FromStructName, 'string')
    fields=ObjectDef["fields"]
    configType=ObjectDef['configType']
    SeqOrAlt=''
    if configType=='SEQ': SeqOrAlt='parseSEQ'
    elif configType=='ALT': SeqOrAlt='parseALT'
    cdlog(logLvl, "WRITING function {}() to extract struct {} from parse tree: stage 2...".format(nameForFunc, ToStructName))
    if configType=='SEQ':
        S+=Write_structExtracter(classes, ToStructName, FromStructName, fields, nameForFunc, logLvl)
    elif configType=='ALT':
        S+=Write_ALT_Extracter(classes, ToStructName, fields, 'SRec', '', 'tmpStr', '    ', -1, logLvl)

    seqExtracter =  "\n    void: "+nameForFunc+"(our stateRec: SRec0, their "+ToStructName+": memStruct) <- {\n" + S + "    }\n"
    extracterFunctionAccumulator += seqExtracter
    #print "########################## extracterFunctionAccumulator\n",extracterFunctionAccumulator,"\n#####################################\n"

def writeParserWrapperFunction(classes, className):
    S='''
struct GLOBAL{
    our <CLASSNAME>: Parse_<CLASSNAME>(me string: textIn) <- {
        me EParser: parser
        parser.populateGrammar()
        parser.initPosStateSets(parser.<CLASSNAME>_str, textIn)
        parser.doParse()
        if (parser.doesParseHaveError()) {
            print("Parse Error:" + parser.errorMesg + "\\n")
        }
        our stateRec: topItem <- parser.resolve(parser.lastTopLevelItem, "")
        our <CLASSNAME>: result
        Allocate(result)
        parser.Extract_<CLASSNAME>_to_<CLASSNAME>(topItem, result)
        return(result)
    }
}
'''.replace('<CLASSNAME>', className)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], S, 'Parse_'+className+'()')

def CreateStructsForStringModels(classes, newClasses, tags):
    # Define fieldResult struct
    #~ structsName = 'fetchResult'
    #~ StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    #~ progSpec.addObject(classes[0], classes[1], structsName, 'struct', 'SEQ')
    #~ codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    if len(newClasses)==0: return
    populateBaseRules()

    global extracterFunctionAccumulator
    extracterFunctionAccumulator=""
    ExtracterCode="""

    me string: makeStr(our stateRec: SRec) <- {
        me string: S <- ""
        me int: startPos <- SRec.originPos
        me int: endPos <- SRec.crntPos
        me int: prod <- SRec.productionID
        if(prod == quotedStr or prod == quotedStr1 or prod == quotedStr2){
            startPos <- startPos+1
            endPos <- endPos-1
        }
        withEach i in RANGE(startPos .. endPos){
            S <- S+textToParse[i]
        }
        return(S)
    }
    me int64: makeInt(our stateRec: SRec) <- {
        me string: S <- makeStr(SRec)
        me int64: N <- stol(S)
        return(N)
    }
    me BigInt: makeHexInt(our stateRec: SRec) <- {
        me string: S <- makeStr(SRec)
        me BigInt: N
        N.hexNumToBigInt(S)
        return(N)
    }
    me BigInt: makeBinInt(our stateRec: SRec) <- {
        me string: S <- makeStr(SRec)
        me BigInt: N
        N.binNumToBigInt(S)
        return(N)
    }
    our stateRec: getNextStateRec(our stateRec: SRec) <- {if(SRec.next){ return(SRec.next)} return(NULL) }
    """

    global nextParseNameID
    nextParseNameID=0
    numStringStructs=0
    for className in newClasses:
        if className[0] == '!': continue
        ObjectDef = classes[0][className]
        if(ObjectDef['stateType'] == 'string'):
            className=className[1:]
            cdlog(1, "  Writing parse system for "+className)
            numStringStructs+=1
            fields    = ObjectDef["fields"]
            configType= ObjectDef['configType']
            classTags = ObjectDef['tags']
            if 'StartSymbol' in classTags:
                writeParserWrapperFunction(classes, className)
            SeqOrAlt=''
            if configType=='SEQ': SeqOrAlt='parseSEQ'   # seq has {}
            elif configType=='ALT': SeqOrAlt='parseALT' # alt has []

            normedObjectName = className.replace('::', '_')
            if normedObjectName==className: normedObjectName+='_str'
            # Write the rules for all the fields, and a parent rule which is either SEQ or ALT, and REP/OPT as needed.
            cdlog(2, "CODING Parser Rules for {}".format(normedObjectName))
            ruleID = writeNonTermParseRule(classes, tags, normedObjectName, fields, SeqOrAlt, '', 3)

            if SeqOrAlt=='parseSEQ':
                [memObj, memVersionName]=fetchMemVersion(classes, className)
                if memObj!=None:
                    Write_Extracter(classes, className, className, 2)
                else: cdlog(2, "NOTE: Skipping {} because it has no struct version defined.".format(className))

    if numStringStructs==0: return

    ExtracterCode += extracterFunctionAccumulator

    ############  Add struct parser
    parserCode=genParserCode()
    codeDogParser.AddToObjectFromText(classes[0], classes[1], parserCode, 'Parser for '+className)

    structsName='EParser'
    progSpec.addObject(classes[0], classes[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode), 'class '+structsName)
