; COMMAND-LINE: cvc4 --lang=sygus2

(set-logic BV)
(set-option :sygus-out status-and-def)
(set-option :e-matching false)

(define-sort BVn () (_ BitVec 4))
(define-sort Stream () (_ BitVec 4))
(define-fun ZERO () Stream (_ bv0 4))
(define-fun ONE () Stream (_ bv1 4))
(define-fun LastIndex () Stream (_ bv3 4))

(define-fun S_FALSE () Stream ZERO)
(define-fun S_TRUE () Stream (bvnot S_FALSE))

(define-fun bvimpl ( (A Stream) (B Stream) ) Stream
  (bvor (bvnot A) B)
)

(define-fun set-m-plus-n-bit-of-A-to-m-bit-of-B ( (A Stream) (n BVn) (B Stream) (m BVn) ) Stream
  (bvor
    A
    (bvshl (bvand B (bvshl ONE m)) n)
  )
)

(define-fun X ((k BVn) (l BVn) (A Stream)) Stream
  (let (( shrA1 (bvlshr A ONE) ))
    (set-m-plus-n-bit-of-A-to-m-bit-of-B shrA1 k shrA1 l)
  )
)

(define-fun rev ((A Stream)) Stream
  (concat
    ((_ extract 0 0) A)
    (concat
      ((_ extract 1 1) A)
      (concat
        ((_ extract 2 2) A)
        ((_ extract 3 3) A)
      )
    )
  )
)

(define-fun reverse ((k BVn) (l BVn) (A Stream)) Stream
  (rev (bvshl A (bvadd LastIndex (bvneg (bvadd k l))) ))
)

(define-fun untilNL ((k BVn) (l BVn) (A Stream) (B Stream)) Stream
  (bvor B
    (bvand A 
      (bvnot (reverse k l (bvadd (reverse k l (bvor A B)) (reverse k l B) )) )
    )
  )
)

(define-fun U ((k BVn) (l BVn) (A Stream) (B Stream)) Stream
  (untilNL k l
    A 
    (set-m-plus-n-bit-of-A-to-m-bit-of-B B k (untilNL k l A B) l)
  )
)

(define-fun F ((k BVn) (l BVn) (A Stream)) Stream
  (U k l S_TRUE A)
)

(define-fun G ((k BVn) (l BVn) (A Stream)) Stream
  (bvnot (F k l (bvnot A)))
)

; l = loop position
; k = last position minus loop position
(synth-fun phi ((k BVn) (l BVn) (x0 Stream) (x1 Stream)) Stream
   ((<f> Stream))
   ((<f> Stream (
     S_TRUE 
     S_FALSE
     ( Variable Stream )
     (bvnot <f>)
     (bvand <f> <f>) 
     (bvor <f> <f>)
     (bvimpl <f> <f>)
     (X k l <f>)
     (U k l <f> <f>)
     (F k l <f>)
     (G k l <f>)
   )))
)

;; Positive examples
(constraint
   (and
    (= ((_ extract 0 0) (phi (_ bv3 4) (_ bv0 4) #b1011 #b1101)) #b1)
    (= ((_ extract 0 0) (phi (_ bv3 4) (_ bv0 4) #b0010 #b1011)) #b1)
    (= ((_ extract 0 0) (phi (_ bv3 4) (_ bv0 4) #b1001 #b1101)) #b1)
    (= ((_ extract 0 0) (phi (_ bv3 4) (_ bv0 4) #b1111 #b0100)) #b1)
   )
)

;; Negative examples
(constraint
   (and
    (= ((_ extract 0 0) (phi (_ bv1 4) (_ bv0 4) #b0000 #b0000)) #b0)
    (= ((_ extract 0 0) (phi (_ bv3 4) (_ bv0 4) #b0100 #b0100)) #b0)
    (= ((_ extract 0 0) (phi (_ bv1 4) (_ bv1 4) #b0001 #b0000)) #b0)
   )
)

; One solution: U(x0, x1)
(check-synth)
